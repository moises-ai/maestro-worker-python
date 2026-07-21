import sys

import pytest

from maestro_worker_python import init


def test_init_creates_complete_worker_scaffold(tmp_path, monkeypatch):
    target = tmp_path / "new-worker"
    monkeypatch.setattr(sys, "argv", ["maestro-init", "--folder", str(target)])
    monkeypatch.setattr(init.metadata, "version", lambda _name: "4.2.0")

    init.main()

    assert (target / "worker.py").is_file()
    assert (target / "pyproject.toml").is_file()
    assert not (target / "requirements.txt").exists()
    assert not (target / "uv.lock").exists()
    assert (target / "docker-compose.yaml").is_file()
    assert (target / "Dockerfile").is_file()
    assert (target / ".gitignore").is_file()
    assert (target / ".dockerignore").is_file()
    assert (target / "models" / ".gitkeep").is_file()
    assert not (target / "models" / "model.th").exists()

    pyproject = (target / "pyproject.toml").read_text()
    assert (
        '"maestro-worker-python @ '
        'https://github.com/moises-ai/maestro-worker-python/'
        'archive/refs/tags/4.2.0.tar.gz"'
        in pyproject
    )

    dockerfile = (target / "Dockerfile").read_text()
    assert "FROM python:3.12-slim-trixie" in dockerfile
    assert (
        "COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /bin/"
        in dockerfile
    )
    assert "UV_LINK_MODE=copy" in dockerfile
    assert "COPY pyproject.toml uv.lock ./" in dockerfile
    assert "--mount=type=cache,target=/root/.cache/uv" in dockerfile
    assert "uv sync --locked --no-dev" in dockerfile
    assert "requirements.txt" not in dockerfile


def test_init_allows_identical_rerun_and_preserves_unrelated_files(
    tmp_path, monkeypatch
):
    target = tmp_path / "existing-directory"
    target.mkdir()
    unrelated_file = target / "notes.txt"
    unrelated_file.write_text("keep me")
    monkeypatch.setattr(sys, "argv", ["maestro-init", "--folder", str(target)])
    monkeypatch.setattr(init.metadata, "version", lambda _name: "4.2.0")

    init.main()
    init.main()

    assert unrelated_file.read_text() == "keep me"


def test_init_aborts_before_overwriting_modified_scaffold_file(
    tmp_path, monkeypatch, capsys
):
    target = tmp_path / "existing-worker"
    target.mkdir()
    worker = target / "worker.py"
    worker.write_text("custom worker")
    monkeypatch.setattr(sys, "argv", ["maestro-init", "--folder", str(target)])
    monkeypatch.setattr(init.metadata, "version", lambda _name: "4.2.0")

    with pytest.raises(SystemExit):
        init.main()

    assert worker.read_text() == "custom worker"
    assert not (target / "pyproject.toml").exists()
    assert "refusing to overwrite modified scaffold files: worker.py" in capsys.readouterr().err
