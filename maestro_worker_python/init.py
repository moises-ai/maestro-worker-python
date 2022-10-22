import shutil
import argparse
import os
import pathlib

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    dir = pathlib.Path(__file__).parent.resolve()
    files = os.listdir(f"{dir}/worker_example")
    for file in files:
        if file == "models":
            continue
        if file == "__init__.py":
            continue
        shutil.copy(f"{dir}/worker_example/{file}", args.get("folder"))
    
    os.mkdir(f"{args.get('folder')}/models")
    shutil.copy(f"{dir}/worker_example/models/model.th", f"{args.get('folder')}/models/model.th")


