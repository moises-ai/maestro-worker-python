from fastapi import FastAPI, Request, Response
import os
import socket
import datetime
from starlette.concurrency import run_in_threadpool
from importlib.machinery import SourceFileLoader


BASE_PATH = os.environ.get("BASE_PATH", "/")
MODEL_PATH = os.environ.get("MODEL_PATH", "./worker.py")

worker = SourceFileLoader("worker",MODEL_PATH).load_module()
model = worker.MoisesWorker()
app = FastAPI()

@app.post(f"{BASE_PATH}/inference")
async def inference(request: Request, response: Response):
    params = await request.json()
    return await run_in_threadpool(model.inference, input_data=params)

@app.get(f"{BASE_PATH}/")
async def index(request: Request):
    return {"hostname": socket.gethostname(), "ok": True, "date": datetime.datetime.now()}

@app.get(f"{BASE_PATH}/health")
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