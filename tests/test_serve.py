import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maestro_worker_python.config import settings

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
