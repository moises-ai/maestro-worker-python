# Maestro Worker Python

This module scaffolds the creation of a standard inference worker to run on the Moises/Maestro infrastructure.

## Installation
To install the main branch:
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git
```

To install a version (recommended):
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git@5.0.0
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
  - A `pyproject.toml` pinned to the installed Maestro worker version
  - A `README.md` covering local, Docker, and PyTorch development
  - A `worker.py` with a worker example

Install the worker dependencies and create its `uv.lock`:

```bash
cd <worker-folder>
uv sync
```

Commit the generated `uv.lock` with the worker project.

The generated README explains how to declare a specific PyTorch version for
local development and select a matching PyTorch base image for container tests.

## Testing your worker

### Using `maestro-cli`:

Run the CLI passing your worker file as the first param, then, any parameters exposed by your class. In this example, `input_1` will be sent to the worker, with the value `Hello`.

```bash
uv run maestro-cli ./worker.py --input_1=Hello
```

### Using `maestro-server`:

Run the maestro server with the path to your worker. To see all options, use `maestro-server --help`

```bash
uv run maestro-server --worker=./worker.py
```

Installed worker adapters can also be loaded by module name:

```bash
uv run maestro-server --worker=my_package.worker
```

Send a request to the server inference endpoint:

```bash
curl --request POST --url http://localhost:8000/inference  --header 'Content-Type: application/json' \
    --data '{"input_1": "Hello"}'
```

Workers return a `WorkerResponse` with three fields:

- `billable_seconds`: the billable duration as a number of seconds, including
  fractional seconds when available, or `null` when it cannot be determined.
- `stats`: numeric worker measurements. Use `duration` for total worker
  processing time; additional keys may report individual phases.
- `result`: the worker-specific JSON object.

The `/health` endpoint reports the worker artifact version supplied through
`WORKER_VERSION` and available GPU metadata in addition to `ok`. Deployments
should set it to the exact worker image tag; it is `null` when unset.
`nvidia_driver_version` is the host driver,
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

The returned `float` preserves fractional seconds reported by `ffprobe`.

## Using Docker Compose

### Build image
```bash
docker compose build
```

### Run the server

```bash
docker compose run --service-ports worker
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

Run the quality checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
