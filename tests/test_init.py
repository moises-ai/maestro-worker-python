import sys

from maestro_worker_python.init import main


def test_init_creates_complete_worker_scaffold(tmp_path, monkeypatch):
    target = tmp_path / "new-worker"
    monkeypatch.setattr(sys, "argv", ["maestro-init", "--folder", str(target)])

    main()

    assert (target / "worker.py").is_file()
    assert (target / "requirements.txt").is_file()
    assert (target / "docker-compose.yaml").is_file()
    assert (target / "Dockerfile").is_file()
    assert (target / ".gitignore").is_file()
    assert (target / ".dockerignore").is_file()
    assert (target / "models" / ".gitkeep").is_file()
    assert not (target / "models" / "model.th").exists()
