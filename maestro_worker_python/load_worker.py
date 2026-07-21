import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_worker(reference: str) -> ModuleType:
    """Load a worker from a Python file path or an importable module name."""
    path = Path(reference)
    if path.suffix != ".py" and not path.exists():
        return importlib.import_module(reference)

    path = path.resolve()
    worker_dir = str(path.parent)
    if worker_dir not in sys.path:
        sys.path.insert(0, worker_dir)

    search_locations = [worker_dir] if path.name == "__init__.py" else None
    spec = importlib.util.spec_from_file_location(
        "worker",
        path,
        submodule_search_locations=search_locations,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load worker from {reference!r}")

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get("worker")
    sys.modules["worker"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous_module is None:
            sys.modules.pop("worker", None)
        else:
            sys.modules["worker"] = previous_module
        raise
    return module
