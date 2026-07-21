import asyncio
import importlib
import sys
from pathlib import Path

import pytest

from maestro_worker_python.config import settings


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
