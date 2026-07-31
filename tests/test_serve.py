import asyncio
import importlib
import sys
import threading
from pathlib import Path

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.transport import Transport

from maestro_worker_python.config import settings
from maestro_worker_python.health import collect_health_metadata
from maestro_worker_python.response import WorkerResponse


class _RecordingScope:
    def __init__(self):
        self.tags: dict[str, str] = {}
        self.fingerprint = None

    def set_tag(self, key, value):
        self.tags[key] = value


def _capture_sentry(monkeypatch: pytest.MonkeyPatch):
    """Record what serve.py's import-time Sentry configuration would do."""
    options: dict = {}
    scope = _RecordingScope()
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: options.update(kwargs))
    monkeypatch.setattr(sentry_sdk, "get_global_scope", lambda: scope)
    return options, scope


class _CapturingTransport(Transport):
    """Transport subclass rather than a function transport, which is deprecated."""

    def __init__(self, events):
        super().__init__()
        self.events = events

    def capture_envelope(self, envelope):
        for item in envelope.items:
            event = item.get_event()
            if event is not None:
                self.events.append(event)


@pytest.fixture
def sentry_events(monkeypatch: pytest.MonkeyPatch):
    """Run the real SDK against a capturing transport, not a stubbed init.

    Release, tags, and fingerprint are only meaningful if the SDK actually
    applies them to an event, which depends on scope semantics a stub cannot
    reproduce.
    """
    events: list[dict] = []
    real_init = sentry_sdk.init

    def init(**options):
        # A dsn is required for the client to be active at all; example.invalid is
        # unresolvable and the capturing transport is what keeps this off the network.
        options["dsn"] = "https://key@example.invalid/1"
        transport = _CapturingTransport(events)
        options["transport"] = transport
        result = real_init(**options)
        assert sentry_sdk.get_client().transport is transport, "would send real events"
        return result

    monkeypatch.setattr(sentry_sdk, "init", init)
    yield events
    # The client and the global scope outlive the test; drop both so later tests
    # neither report into this transport nor inherit its identity.
    sentry_sdk.get_global_scope().clear()
    real_init(dsn=None)


# Deliberately mixed value types: `internal` is typed only as an object, so
# coercion of anything inside it would be a silent corruption of a channel this
# library is supposed to be agnostic about.
INTERNAL_PAYLOAD = {
    "file_transfers": [
        {"direction": "input", "field": "input_url", "url": "https://host/in.mp3", "bytes": 0},
        {"direction": "output", "field": "vocals", "url": "https://host/out%2Fa.wav", "bytes": 1234},
    ],
    "nested": {"flag": True, "count": 7, "ratio": 0.5, "absent": None},
}


def _write_worker(worker_path: Path, returned: str) -> None:
    worker_path.write_text(
        f"INTERNAL = {INTERNAL_PAYLOAD!r}\n"
        "class MoisesWorker:\n"
        "    def inference(self, input_data):\n"
        f"        return {returned}\n"
    )


def _import_serve(monkeypatch: pytest.MonkeyPatch, worker_path: Path):
    monkeypatch.setattr(settings, "model_path", str(worker_path))
    monkeypatch.setattr(settings, "sentry_dsn", None)
    monkeypatch.setattr(settings, "enable_json_logging", False)
    sys.modules.pop("maestro_worker_python.serve", None)
    return importlib.import_module("maestro_worker_python.serve")


@pytest.fixture
def serve_module(tmp_path, monkeypatch):
    worker_path = tmp_path / "worker.py"
    worker_path.write_text("class MoisesWorker:\n    pass\n")
    return _import_serve(monkeypatch, worker_path)


def test_lifespan_creates_ready_file_and_cleans_up_on_shutdown(serve_module, tmp_path, monkeypatch):
    ready_path = tmp_path / "http_ready"
    events: list[str] = []

    monkeypatch.setattr(serve_module, "HTTP_READY_PATH", str(ready_path))
    monkeypatch.setattr(serve_module, "get_health_metadata", lambda: events.append("health") or {})
    monkeypatch.setattr(serve_module, "kill_child_processes", lambda: events.append("kill"))

    async def run():
        assert not ready_path.exists()
        async with serve_module.lifespan(serve_module.app):
            assert events == ["health"]
            assert ready_path.read_text() == "Ready to serve"
        assert events == ["health", "kill"]
        assert not ready_path.exists()

    asyncio.run(run())


def test_lifespan_shutdown_tolerates_missing_ready_file(serve_module, tmp_path, monkeypatch):
    ready_path = tmp_path / "http_ready"
    monkeypatch.setattr(serve_module, "HTTP_READY_PATH", str(ready_path))
    monkeypatch.setattr(serve_module, "get_health_metadata", lambda: {})
    monkeypatch.setattr(serve_module, "kill_child_processes", lambda: None)

    async def run():
        async with serve_module.lifespan(serve_module.app):
            ready_path.unlink()
            assert not ready_path.exists()

    asyncio.run(run())
    assert not ready_path.exists()


def test_inference_passes_internal_content_through_uninspected(tmp_path, monkeypatch):
    worker_path = tmp_path / "worker.py"
    _write_worker(
        worker_path,
        '{"billable_seconds": 1.0, "stats": {"duration": 0.5}, "result": {"ok": True}, "internal": INTERNAL}',
    )
    serve_module = _import_serve(monkeypatch, worker_path)

    body = TestClient(serve_module.app).post("/inference", json={}).json()

    assert body["internal"] == INTERNAL_PAYLOAD
    nested = body["internal"]["nested"]
    # Equality alone would accept 7 becoming 7.0 or True becoming 1.
    assert isinstance(nested["count"], int) and not isinstance(nested["count"], bool)
    assert isinstance(nested["flag"], bool)
    assert body["result"] == {"ok": True}


def test_inference_drops_a_field_the_response_model_does_not_declare(tmp_path, monkeypatch):
    """The single declared passthrough is what keeps the envelope closed."""
    worker_path = tmp_path / "worker.py"
    _write_worker(
        worker_path,
        '{"billable_seconds": 1.0, "stats": {}, "result": {}, "internal": {}, "leaked": "not for callers"}',
    )
    serve_module = _import_serve(monkeypatch, worker_path)

    body = TestClient(serve_module.app).post("/inference", json={}).json()

    assert "leaked" not in body


def test_inference_distinguishes_an_empty_internal_object_from_no_internal_object(tmp_path, monkeypatch):
    """Producers signal support with the object itself, so the two must not collapse."""
    worker_path = tmp_path / "worker.py"
    _write_worker(worker_path, '{"billable_seconds": 1.0, "stats": {}, "result": {}, "internal": {}}')
    serve_module = _import_serve(monkeypatch, worker_path)
    empty = TestClient(serve_module.app).post("/inference", json={}).json()

    _write_worker(worker_path, '{"billable_seconds": 1.0, "stats": {}, "result": {}}')
    serve_module = _import_serve(monkeypatch, worker_path)
    unset = TestClient(serve_module.app).post("/inference", json={}).json()

    assert empty["internal"] == {}
    assert unset["internal"] is None


def test_sentry_events_carry_the_worker_identity_from_a_worker_thread(tmp_path, monkeypatch, sentry_events):
    monkeypatch.setattr(settings, "worker_name", "dmx-bass-xl-a")
    monkeypatch.setattr(settings, "worker_version", "d41d8cd98f00b204")
    worker_path = tmp_path / "worker.py"
    worker_path.write_text("class MoisesWorker:\n    pass\n")

    _import_serve(monkeypatch, worker_path)

    # inference() hands the worker body to a threadpool, so the identity has to
    # survive leaving the request's own scope.
    def capture_from_thread():
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            sentry_sdk.capture_exception()

    thread = threading.Thread(target=capture_from_thread)
    thread.start()
    thread.join()
    sentry_sdk.flush()

    (event,) = sentry_events
    # The release must stay the value /health reports for the same process.
    assert event["release"] == "d41d8cd98f00b204"
    assert collect_health_metadata()["worker"]["version"] == "d41d8cd98f00b204"
    assert event["tags"]["worker"] == "dmx-bass-xl-a"
    # Grouping is per worker, so one family base cannot collapse the fleet into
    # a single issue.
    assert event["fingerprint"] == ["{{ default }}", "dmx-bass-xl-a"]


def test_sentry_keeps_its_own_release_discovery_when_identity_is_unset(tmp_path, monkeypatch):
    options, scope = _capture_sentry(monkeypatch)
    monkeypatch.setattr(settings, "worker_name", None)
    monkeypatch.setattr(settings, "worker_version", None)
    worker_path = tmp_path / "worker.py"
    worker_path.write_text("class MoisesWorker:\n    pass\n")

    _import_serve(monkeypatch, worker_path)

    assert options["release"] is None
    assert scope.tags == {}
    assert scope.fingerprint is None


def test_inference_stamps_the_deployment_identity_over_worker_supplied_values(serve_module, monkeypatch):
    monkeypatch.setattr(settings, "worker_name", "dmx-bass-xl-a")
    monkeypatch.setattr(settings, "worker_version", "d41d8cd98f00b204")

    # A worker supplying a partial identity has the whole object replaced, not
    # merged, so a spoofed member cannot survive alongside a stamped one.
    from_dict = serve_module._with_worker_identity(
        {"billable_seconds": 1.0, "stats": {}, "result": {"ok": True}, "worker": {"version": "spoofed"}}
    )
    from_model = serve_module._with_worker_identity(WorkerResponse(billable_seconds=1.0, stats={}, result={"ok": True}))

    for stamped in (from_dict, from_model):
        assert stamped["worker"] == {"name": "dmx-bass-xl-a", "version": "d41d8cd98f00b204"}
        assert stamped["result"] == {"ok": True}


def test_inference_leaves_unrecognized_worker_return_shapes_alone(serve_module, monkeypatch):
    monkeypatch.setattr(settings, "worker_version", "d41d8cd98f00b204")

    assert serve_module._with_worker_identity(None) is None


def test_inference_and_health_report_the_identity_over_http(tmp_path, monkeypatch):
    """The response envelope is a cross-service contract, so pin the wire shape."""
    monkeypatch.setattr(settings, "worker_name", "dmx-bass-xl-a")
    monkeypatch.setattr(settings, "worker_version", "d41d8cd98f00b204")
    worker_path = tmp_path / "worker.py"
    worker_path.write_text(
        "class MoisesWorker:\n"
        "    def inference(self, input_data):\n"
        "        return {\n"
        '            "billable_seconds": 2.0,\n'
        '            "stats": {"duration": 0.5},\n'
        '            "result": {"echo": input_data},\n'
        "        }\n"
    )
    serve_module = _import_serve(monkeypatch, worker_path)
    client = TestClient(serve_module.app)

    inference = client.post("/inference", json={"input_url": "gs://bucket/song.mp3"}).json()
    health = client.get("/health").json()

    assert inference["worker"] == {"name": "dmx-bass-xl-a", "version": "d41d8cd98f00b204"}
    assert inference["result"] == {"echo": {"input_url": "gs://bucket/song.mp3"}}
    assert inference["billable_seconds"] == 2.0
    # Both surfaces read one Settings field each, so they cannot disagree.
    assert health["worker"] == inference["worker"]
