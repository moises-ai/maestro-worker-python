# Maestro Worker Python

This module scaffolds the creation of a standard inference worker to run on the Moises/Maestro infrastructure.

## Installation
To install the main branch:
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git
```

To install a version (recommended):
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git@4.0.0
```

## Maestro init
Run the init script to scaffold a maestro worker in the current directory.

To create a different one, use the flag `--folder`

```bash
maestro-init
```

This will create a starter Maestro worker project, including:
  - A `models` folder to include your models
  - A `.gitignore` and `.dockerignore`
  - A `docker-compose.yaml` file
  - A `Dockerfile`
  - A `requirements.txt` file including this package
  - A `worker.py` with a worker example

## Testing your worker

### Using `maestro-cli`:

Run the CLI passing your worker file as the first param, then, any parameters exposed by your class. In this example, `input_1` will be sent to the worker, with the value `Hello`.

```bash
maestro-cli ./worker.py --input_1=Hello
```

### Using `maestro-server`:

Run the maestro server with the path to your worker. To see all options, use `maestro-server --help`

```bash
maestro-server --worker=./worker.py
```

Installed worker adapters can also be loaded by module name:

```bash
maestro-server --worker=my_package.worker
```

Send a request to the server inference endpoint:

```bash
curl --request POST --url http://localhost:8000/inference  --header 'Content-Type: application/json' \
    --data '{"input_1": "Hello"}'
```

The `/health` endpoint reports the Maestro worker package version and available
GPU metadata in addition to `ok`. `nvidia_driver_version` is the host driver,
`driver_supported_version` is the newest CUDA version it supports, and
`torch_build_version` is the toolkit version used to build an already-imported
PyTorch. NVIDIA host probing uses NVML and is best-effort, so CPU workers return
an empty `hardware.gpus` list. Visible MIG partitions report their GPU-instance
slice count, compute-instance slice count, and memory size. MPS reports its
configured active-thread percentage and pinned-device-memory limit. These
client settings can be further constrained by the MPS daemon, so they are not
presented as effective limits and cannot reliably reveal the total number of
clients. Once an already-imported PyTorch has initialized CUDA,
`observed_sm_count` reports the SMs available to its current CUDA device without
making the health check initialize CUDA itself.

### Upload/Download server for development purposes
In order to avoid using signedurls for uploading/downloading files, you can use the `maestro-upload-server` command. This will start a server in the default `9090` port that will upload/download files in the local `./uploads` folder.

Examples:

```bash
maestro-upload-server --port=9090
```

After server is running, you can upload files to it:

```bash
curl http://localhost:9090/upload-file/your_file_name
```

Then retrieve it:

```bash
curl http://localhost:9090/get-file/your_file_name
```

You can clean the files using:

```bash
curl http://localhost:9090/clean
```

You can also list files using:
```bash
curl http://localhost:9090/list-files
```

## Worker Utils

### Download a file from URL:
```python
from maestro_worker_python.download_file import download_file

file_name = download_file("https://url_to_download_file")
```

### Upload files to signed_url:
```python
from maestro_worker_python.upload_files import upload_files, UploadFile

files_to_upload = []
files_to_upload.append(UploadFile(file_path="test_upload1.txt", file_type="text/plain", signed_url="https://httpbin.org/put"))
files_to_upload.append(UploadFile(file_path="test_upload2.txt", file_type="text/plain", signed_url="https://httpbin.org/put"))
upload_files(files_to_upload)
```

### Convert media files:
```python
from maestro_worker_python.convert_files import convert_files, FileToConvert

files_to_convert = []
files_to_convert.append(FileToConvert(input_file_path="input.mp3", output_file_path="output.wav", file_format="wav", max_duration=1200))
files_to_convert.append(FileToConvert(input_file_path="input.mp3", output_file_path="output.m4a", file_format="m4a", max_duration=1200))
convert_files(files_to_convert)
```

### Get file duration in seconds
```python
from maestro_worker_python.get_duration import get_duration
get_duration('./myfile.mp3')
```

## Using Docker Compose

### Build image
```bash
docker-compose build
```

### Run the server

```bash
docker-compose run --service-ports worker
```

### Developing this package

Install [uv](https://docs.astral.sh/uv/getting-started/installation/).

You can run it in development mode:

```bash
uv sync
uv run maestro-init
```

To bump the package version:

```bash
uv version --bump patch
```

Running tests:

```bash
uv run pytest
```
