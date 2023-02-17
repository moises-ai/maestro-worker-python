import uvicorn
import logging
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()
    logging.info("Starting upload server on folder ./uploads using port 9090")
    uvicorn.run("maestro_worker_python.upload_server:app",
                host="0.0.0.0", port=args.port, log_level='info'
                )
