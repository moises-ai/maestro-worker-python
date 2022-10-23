import shutil
import argparse
import os
import pathlib
from xml.etree.ElementInclude import include

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    dir = pathlib.Path(__file__).parent.resolve()
    shutil.copy(f"{dir}/data/worker.py", f"{args.get('folder')}/worker.py")
    shutil.copy(f"{dir}/data/requirements.txt", f"{args.get('folder')}/requirements.txt")
    shutil.copy(f"{dir}/data/docker-compose.yaml", f"{args.get('folder')}/docker-compose.yaml")
    shutil.copy(f"{dir}/data/Dockerfile", f"{args.get('folder')}/Dockerfile")
    os.mkdir(f"{args.get('folder')}/models")
    shutil.copy(f"{dir}/data/models/model.th", f"{args.get('folder')}/models/model.th")
    



