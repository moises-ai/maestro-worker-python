import os
import signal
import socket
import datetime
import logging
import json_logging
import traceback
import asyncio
import sentry_sdk
import pydantic
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from importlib.machinery import SourceFileLoader
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .response import ValidationError, WorkerResponse


def filter_transactions(event, hint):
    parsed_url = urlparse(event["request"]["url"])

    if parsed_url.path == "/health":
        return None

    return event


sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=settings.sentry_traces_sample_rate,
    sample_rate=settings.sentry_errors_sample_rate,
    environment=settings.environment,
    before_send_transaction=filter_transactions,
)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
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

worker = SourceFileLoader("worker", settings.model_path).load_module()
model = worker.MoisesWorker()

error_counter = 0
lock = asyncio.Lock()


@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc: Exception):
    global error_counter
    tb = ''.join(traceback.format_exception(None, exc, exc.__traceback__))
    try:
        return JSONResponse(status_code=500, content=jsonable_encoder({"error":  tb}))
    finally:
        if error_counter > 2:
            logging.error("Too many consecutive errors, shutting down worker")
            os.kill(os.getpid(), signal.SIGINT)

        async with lock:
            error_counter += 1


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content=jsonable_encoder({"error":  exc.reason}))


@app.exception_handler(pydantic.error_wrappers.ValidationError)
async def validation_error_handler_pydantic(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content=jsonable_encoder({"error":  exc.errors()}))


@app.post("/inference", response_model=WorkerResponse)
async def inference(request: Request):
    global error_counter
    params = await request.json()
    result = await run_in_threadpool(model.inference, input_data=params)
    async with lock:
        error_counter = 0
    return result


@app.get("/")
async def index(request: Request):
    return {"hostname": socket.gethostname(), "ok": True, "date": datetime.datetime.now()}


@app.get("/health")
async def health(request: Request):
    return {"ok": True}


@app.on_event("shutdown")
def shutdown_event():
    print("Shutting down, bye bye")
    os.remove("/tmp/http_ready")


@app.on_event("startup")
def startup_event():
    # Create a file to indicate that the server is running
    with open("/tmp/http_ready", "a") as f:
        f.write("Ready to serve")
