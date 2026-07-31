import asyncio
import datetime
import logging
import os
import socket
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlparse

import json_logging
import pydantic
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import settings
from .health import get_health_metadata
from .kill_process import kill_child_processes, terminate_current_process
from .load_worker import load_worker
from .response import ValidationError, WorkerResponse


def filter_transactions(event, hint):
    parsed_url = urlparse(event["request"]["url"])

    if parsed_url.path == "/health":
        return None

    return event


sentry_sdk.init(
    dsn=settings.sentry_dsn,
    # Same value /health reports; unset falls back to SENTRY_RELEASE / VCS discovery.
    release=settings.worker_version,
    traces_sample_rate=settings.sentry_traces_sample_rate,
    sample_rate=settings.sentry_errors_sample_rate,
    environment=settings.environment,
    before_send_transaction=filter_transactions,
)

if settings.worker_name:
    # Global scope so the tag survives threadpool work (isolation scope would not).
    scope = sentry_sdk.get_global_scope()
    scope.set_tag("worker", settings.worker_name)
    # Shared family bases share stacktraces; pin grouping to the worker name.
    scope.fingerprint = ["{{ default }}", settings.worker_name]


HTTP_READY_PATH = "/tmp/http_ready"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Prime the cache before readiness probes start hitting /health.
    get_health_metadata()
    with open(HTTP_READY_PATH, "a") as ready_file:
        ready_file.write("Ready to serve")

    try:
        yield
    finally:
        logging.info("Shutting down, bye bye")
        kill_child_processes()
        with suppress(FileNotFoundError):
            os.remove(HTTP_READY_PATH)


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    # ty does not yet model Starlette's class-based middleware factory protocol.
    CORSMiddleware,  # ty: ignore[invalid-argument-type]
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(level=settings.log_level.upper())

if settings.enable_json_logging:
    json_logging.init_fastapi(enable_json=True)
    json_logging.init_request_instrument(app)
    json_logging.config_root_logger()

worker = load_worker(settings.model_path)
model = worker.MoisesWorker()

error_counter = 0
lock = asyncio.Lock()


@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc: Exception):
    global error_counter
    tb = "".join(traceback.format_exception(None, exc, exc.__traceback__))
    try:
        return JSONResponse(status_code=500, content=jsonable_encoder({"error": tb}))
    finally:
        if error_counter > 10:
            logging.error("Too many consecutive errors, shutting down worker")
            terminate_current_process()

        async with lock:
            error_counter += 1


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content=jsonable_encoder({"error": exc.reason}))


@app.exception_handler(pydantic.ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: pydantic.ValidationError):
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


def _with_worker_identity(result):
    """Stamp deployment identity onto the worker result.

    Returns a mapping so FastAPI still validates the response model (500 on
    bad worker output); validating here would turn that into a 400.
    """
    identity = {
        "worker": {
            "name": settings.worker_name,
            "version": settings.worker_version,
        }
    }

    if isinstance(result, pydantic.BaseModel):
        return {**result.model_dump(), **identity}

    if isinstance(result, dict):
        return {**result, **identity}

    return result


@app.post("/inference", response_model=WorkerResponse)
async def inference(request: Request):
    global error_counter
    params = await request.json()
    result = await run_in_threadpool(model.inference, input_data=params)
    async with lock:
        error_counter = 0
    return _with_worker_identity(result)


@app.get("/")
async def index(request: Request):
    return {"hostname": socket.gethostname(), "ok": True, "date": datetime.datetime.now()}


@app.get("/health")
async def health(request: Request):
    return {"ok": True, **get_health_metadata()}
