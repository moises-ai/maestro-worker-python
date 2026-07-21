import argparse
import logging
import pathlib
import shutil


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    template_dir = pathlib.Path(__file__).parent.resolve() / "data"
    print(r"""___  ___                _
|  \/  |               | |
| .  . | __ _  ___  ___| |_ _ __ ___
| |\/| |/ _` |/ _ \/ __| __| '__/ _ \
| |  | | (_| |  __/\__ \ |_| | | (_) |
\_|  |_/\__,_|\___||___/\__|_|  \___/

""")
    target_dir = pathlib.Path(args.get("folder"))
    logging.info(f"Initializing Maestro worker on folder: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, target_dir, dirs_exist_ok=True)
