import subprocess
import sys
import textwrap

import json_logging
import pytest
from starlette.requests import Request

from maestro_worker_python.request_logging import (
    ClientSafeRequestInfoExtractor,
    register_client_safe_request_extractor,
)


def _request(client: tuple[str, int] | None) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/health", "headers": [], "client": client})


@pytest.fixture
def extractor() -> ClientSafeRequestInfoExtractor:
    return ClientSafeRequestInfoExtractor()


def test_reports_peer_address_when_present(extractor):
    request = _request(("10.0.0.1", 54321))
    assert extractor.get_remote_ip(request) == "10.0.0.1"
    assert extractor.get_remote_port(request) == 54321


def test_reports_empty_value_when_peer_is_gone(extractor):
    request = _request(None)
    assert extractor.get_remote_ip(request) == json_logging.EMPTY_VALUE
    assert extractor.get_remote_port(request) == json_logging.EMPTY_VALUE


def test_registration_replaces_only_the_request_extractor(monkeypatch: pytest.MonkeyPatch):
    before = json_logging._framework_support_map["fastapi"]
    monkeypatch.setitem(json_logging._framework_support_map, "fastapi", dict(before))

    register_client_safe_request_extractor()

    after = json_logging._framework_support_map["fastapi"]
    assert after["request_info_extractor_class"] is ClientSafeRequestInfoExtractor
    assert {k: v for k, v in after.items() if k != "request_info_extractor_class"} == {
        k: v for k, v in before.items() if k != "request_info_extractor_class"
    }


# json_logging's init mutates process-wide logging state and caches the extractor in a
# singleton, so the serving path can only be exercised honestly in a fresh interpreter.
SERVE_A_REQUEST_WITHOUT_A_PEER = """
import asyncio, sys
from maestro_worker_python import serve

scope = {
    "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "scheme": "http",
    "method": "GET", "path": "/health", "raw_path": b"/health", "query_string": b"",
    "root_path": "", "headers": [], "client": None, "server": ("testserver", 80),
}

async def receive():
    return {"type": "http.request", "body": b"", "more_body": False}

messages = []

async def send(message):
    messages.append(message)

asyncio.run(serve.app(scope, receive, send))
print([m["status"] for m in messages if m["type"] == "http.response.start"], file=sys.stderr)
"""


def test_serving_a_request_without_a_peer_logs_cleanly(tmp_path):
    worker_path = tmp_path / "worker.py"
    worker_path.write_text("class MoisesWorker:\n    pass\n")

    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(SERVE_A_REQUEST_WITHOUT_A_PEER)],
        capture_output=True,
        text=True,
        env={"ENABLE_JSON_LOGGING": "true", "MODEL_PATH": str(worker_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "[200]" in result.stderr
    assert "Logging error" not in result.stderr, result.stderr
