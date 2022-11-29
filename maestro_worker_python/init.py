import shutil
import argparse
import os
import pathlib
import logging
from xml.etree.ElementInclude import include

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--folder", default="./",
                        help="Folder to create the worker in")

    args = parser.parse_args().__dict__

    dir = pathlib.Path(__file__).parent.resolve()
    print("""\
___  ___                _             
|  \/  |               | |            
| .  . | __ _  ___  ___| |_ _ __ ___  
| |\/| |/ _` |/ _ \/ __| __| '__/ _ \ 
| |  | | (_| |  __/\__ \ |_| | | (_) |
\_|  |_/\__,_|\___||___/\__|_|  \___/ 
                                                                          
""")
    logging.info(f"Initializing Maestro worker on folder: {args.get('folder')}")
    shutil.copy(f"{dir}/data/worker.py", f"{args.get('folder')}/worker.py")
    shutil.copy(f"{dir}/data/requirements.txt", f"{args.get('folder')}/requirements.txt")
    shutil.copy(f"{dir}/data/docker-compose.yaml", f"{args.get('folder')}/docker-compose.yaml")
    shutil.copy(f"{dir}/data/Dockerfile", f"{args.get('folder')}/Dockerfile")
    os.mkdir(f"{args.get('folder')}/models")
    shutil.copy(f"{dir}/data/models/model.th", f"{args.get('folder')}/models/model.th")
    



