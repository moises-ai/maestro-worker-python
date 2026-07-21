import sys

from maestro_worker_python.load_worker import load_worker


def test_load_worker_file_supports_sibling_imports(tmp_path):
    (tmp_path / "helper.py").write_text('MESSAGE = "loaded locally"\n')
    worker_path = tmp_path / "worker.py"
    worker_path.write_text("from helper import MESSAGE\n")

    original_path = sys.path.copy()
    try:
        module = load_worker(str(worker_path))
    finally:
        sys.path = original_path
        sys.modules.pop("helper", None)
        sys.modules.pop("worker", None)

    assert module.MESSAGE == "loaded locally"


def test_load_worker_imports_module_reference(tmp_path, monkeypatch):
    module_name = "maestro_test_adapter"
    (tmp_path / f"{module_name}.py").write_text('MARKER = "loaded by name"\n')
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        module = load_worker(module_name)
    finally:
        sys.modules.pop(module_name, None)

    assert module.MARKER == "loaded by name"


def test_load_worker_package_supports_relative_imports(tmp_path):
    worker_dir = tmp_path / "worker"
    worker_dir.mkdir()
    (worker_dir / "helper.py").write_text('MESSAGE = "loaded relatively"\n')
    (worker_dir / "__init__.py").write_text("from .helper import MESSAGE\n")

    original_path = sys.path.copy()
    try:
        module = load_worker(str(worker_dir / "__init__.py"))
    finally:
        sys.path = original_path
        sys.modules.pop("worker.helper", None)
        sys.modules.pop("worker", None)

    assert module.MESSAGE == "loaded relatively"
