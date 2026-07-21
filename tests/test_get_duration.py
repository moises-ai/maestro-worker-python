import maestro_worker_python.get_duration as duration_module


def test_get_duration_preserves_fractional_seconds(monkeypatch):
    monkeypatch.setattr(duration_module, "check_output", lambda _command: b"42.711293\n")

    assert duration_module.get_duration("audio.wav") == 42.711293
