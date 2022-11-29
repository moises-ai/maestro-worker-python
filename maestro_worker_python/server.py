import uvicorn
import argparse
import os
import logging


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--worker", default="./worker.py",
                        help="Path to the Moises worker file that include a MoisesWorker class")
    parser.add_argument("--base_path", default="/",
                        help="DEPRECATED")
    parser.add_argument("--port", default=8000, help="Port to run uvicorn on")
    parser.add_argument("--reload", default=False,
                        help="Reload the server on code changes")

    args = parser.parse_args().__dict__
    logging.info(f"Running maestro server with {str(args)}")
    os.environ["MODEL_PATH"] = args.get("worker")

    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'default_handler': {
                'class': 'logging.StreamHandler',
                'level': log_level,
            },
        },
        'loggers': {
            '': {
                '#handlers': ['default_handler'],
            },
            'root': {
                '#handlers': ['default_handler'],
            }
        }
    }
    uvicorn.run(
        "maestro_worker_python.serve:app", host='0.0.0.0', port=int(args.get("port")), reload=args.get("reload"),
        log_level=log_level.lower(), log_config=logging_config,
    )
