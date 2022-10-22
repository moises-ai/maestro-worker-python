from importlib.machinery import SourceFileLoader
import sys

def main():
    worker = SourceFileLoader("worker",sys.argv[1]).load_module()
    model = worker.MoisesWorker()
    params = {}
    for arg in sys.argv:
        if arg.startswith("--"):
            key, value = arg[2:].split("=",1)
            params[key] = value

    print("Running with", params)
    data = model.inference(params)
    print(data)