from importlib.metadata import distribution

import pytest

EXPECTED_SCRIPTS = {
    "maestro-cli": "maestro_worker_python.cli:main",
    "maestro-init": "maestro_worker_python.init:main",
    "maestro-server": "maestro_worker_python.server:main",
    "maestro-upload-server": "maestro_worker_python.run_upload_server:main",
}


@pytest.mark.parametrize("name,value", EXPECTED_SCRIPTS.items())
def test_console_script_is_registered(name, value):
    scripts = {
        ep.name: ep
        for ep in distribution("maestro-worker-python").entry_points
        if ep.group == "console_scripts"
    }
    assert name in scripts
    assert scripts[name].value == value
    assert callable(scripts[name].load())
