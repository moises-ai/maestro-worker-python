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

    files = os.listdir("{dir}/worker_example")
    shutil.copytree(files, args.get("folder"))


