import logging
import sys

from .load_worker import load_worker


def main():
    worker = load_worker(sys.argv[1])
    model = worker.MoisesWorker()
    params = {}
    for arg in sys.argv:
        if arg.startswith("--"):
            key, value = arg[2:].split("=", 1)
            params[key] = value

    logging.info("Running with", params)
    data = model.inference(params)
    logging.info(data)
