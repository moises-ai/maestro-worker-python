import shutil
import argparse
import os
import pathlib

dir = pathlib.Path(__file__).parent.resolve()

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    files = os.listdir(f"{dir}/worker-example/")
    print(files)
    for file in files:
        if file == "models":
            continue
        shutil.copy(f"{dir}/worker-example/{file}", args.get("folder"))
    
    os.mkdir(f"{args.get('folder')}/models")
    shutil.copy(f"{dir}/worker-example/models/model.th", f"{args.get('folder')}/models/model.th")


