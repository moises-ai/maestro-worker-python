import os
from glob import glob
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

app = FastAPI()

@app.put("/upload-file/{filename}")
async def put_file(filename: str, request: Request):
    data = await request.body()
    destination_file_path = "uploads/" + filename  # location to store file
    destination_dir = os.path.dirname(destination_file_path)
    os.makedirs(destination_dir, exist_ok=True)
    with open(destination_file_path, "wb") as f:
        f.write(data)
    return {"result": "OK"}


@app.get("/get-file/{filename}")
async def get_file(filename: str):
    file_path = "uploads/" + filename
    if os.path.exists(file_path):
        return FileResponse(path=file_path, media_type="application/octet-stream", filename=filename)
    return f"File {filename} does not exist."


@app.get("/delete-file/{filename}")
async def delete_file(filename: str):
    file_path = "uploads/" + filename
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"result": "OK"}


@app.get("/clean")
async def clean():
    for file in glob("uploads/*"):
        os.remove(file)
    return {"result": "OK"}


@app.get("/list-files")
async def list_files():
    return {"files": glob("uploads/*")}