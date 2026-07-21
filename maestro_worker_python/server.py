import argparse
import logging
import os

import uvicorn


def _parse_bool(value: str) -> bool:
    normalized = value.casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected a boolean value, got {value!r}")


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--worker", default="./worker.py", help="Python file or importable module that contains a MoisesWorker class"
    )
    parser.add_argument("--base_path", default="/", help="DEPRECATED")
    parser.add_argument("--port", type=int, default=8000, help="Port to run uvicorn on")
    parser.add_argument("--reload", type=_parse_bool, default=False, help="Reload the server on code changes")

    args = parser.parse_args()
    logging.info(f"Running maestro server with {str(args)}")
    os.environ["MODEL_PATH"] = args.worker

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "default_handler": {
                "class": "logging.StreamHandler",
                "level": log_level,
            },
        },
        "loggers": {
            "": {
                "#handlers": ["default_handler"],
            },
            "root": {
                "#handlers": ["default_handler"],
            },
        },
    }
    uvicorn.run(
        "maestro_worker_python.serve:app",
        host="0.0.0.0",
        port=args.port,
        reload=args.reload,
        log_level=log_level.lower(),
        log_config=logging_config,
    )
