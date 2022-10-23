import uvicorn
import argparse
import os


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--worker", default="./worker.py",
                        help="Path to the Moises worker file that include a MoisesWorker class")
    parser.add_argument("--base_path", default="/",
                        help="Base path for the API, example: /your-worker")
    parser.add_argument("--port", default=8000, help="Port to run uvicorn on")
    parser.add_argument("--reload", default=False,
                        help="Reload the server on code changes")
                        
    args = parser.parse_args().__dict__
    print(f"Running maestro server with {str(args)}")
    os.environ["MODEL_PATH"] = args.get("worker")
    os.environ["BASE_PATH"] = args.get("base_path")
    uvicorn.run("maestro_worker_python.serve:app", host='0.0.0.0', port=args.get(
        "port"), reload=args.get("reload"), workers=1)
