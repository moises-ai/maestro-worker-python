import argparse
import logging
import pathlib
import shutil
from importlib import metadata
from tempfile import TemporaryDirectory


_VERSION_PLACEHOLDER = "MAESTRO_WORKER_PYTHON_VERSION"


def _find_conflicts(
    scaffold_dir: pathlib.Path, target_dir: pathlib.Path
) -> list[pathlib.Path]:
    conflicts = []
    for scaffold_path in sorted(scaffold_dir.rglob("*")):
        relative_path = scaffold_path.relative_to(scaffold_dir)
        target_path = target_dir / relative_path
        if not target_path.exists() and not target_path.is_symlink():
            continue

        if target_path.is_symlink():
            conflicts.append(relative_path)
        elif scaffold_path.is_dir():
            if not target_path.is_dir():
                conflicts.append(relative_path)
        elif not target_path.is_file() or (
            scaffold_path.read_bytes() != target_path.read_bytes()
        ):
            conflicts.append(relative_path)

    return conflicts


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    scaffold_dir = pathlib.Path(__file__).parent.resolve() / "scaffold"
    target_dir = pathlib.Path(args.get("folder"))
    if target_dir.is_symlink() or (target_dir.exists() and not target_dir.is_dir()):
        parser.error(f"target path is not a directory: {target_dir}")

    with TemporaryDirectory() as temporary_dir:
        rendered_scaffold_dir = pathlib.Path(temporary_dir)
        shutil.copytree(scaffold_dir, rendered_scaffold_dir, dirs_exist_ok=True)

        pyproject_path = rendered_scaffold_dir / "pyproject.toml"
        pyproject = pyproject_path.read_text().replace(
            _VERSION_PLACEHOLDER,
            metadata.version("maestro-worker-python"),
        )
        pyproject_path.write_text(pyproject)

        conflicts = _find_conflicts(rendered_scaffold_dir, target_dir)
        if conflicts:
            conflict_list = ", ".join(str(path) for path in conflicts)
            parser.error(
                f"refusing to overwrite modified scaffold files: {conflict_list}"
            )

        print(r"""___  ___                _
|  \/  |               | |
| .  . | __ _  ___  ___| |_ _ __ ___
| |\/| |/ _` |/ _ \/ __| __| '__/ _ \
| |  | | (_| |  __/\__ \ |_| | | (_) |
\_|  |_/\__,_|\___||___/\__|_|  \___/

""")
        logging.info(f"Initializing Maestro worker on folder: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(rendered_scaffold_dir, target_dir, dirs_exist_ok=True)
