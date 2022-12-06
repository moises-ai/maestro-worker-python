# Maestro Worker Python

This module scaffolds the creation of a standard inference worker to run on the Moises/Maestro infra-structure.

## Installation
To install the main branch:
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git
```

To install a version (recommended):
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git2.0.2
```

## Maestro init
Run the init script to scaffold a maestro worker in the current directory. 

To create in a different one, use the flag `--folder`

```bash
maestro-init
```

This will create a starter Maestro worker project, including:
  - A `models` folder to include your models
  - A `docker-compose.yaml`file
  - A `DockerFile`
  - A `requirements.txt` file including this package
  - A `worker.py` with a worker example

## Testing your worker

### Using `maestro-cli`:

Run the CLI passing your worker file as the first param, then, any parameters exposed by your class. In this example, `input_1` will be sent to the worker, with the value `Hello`.

```bash
maestro-cli ./worker.py --input_1=Hello
```

### Using `maestro-server`:

Run the maestro server with the path to your worker and the base path you would like it to run. To see all options, use `maestro-server --help`

```bash
maestro-server --worker=./worker.py --base_path=/worker-example
```

Send a request to the server inference endpoint:

```bash
curl --request POST --url http://localhost:8000/worker-example/inference  --header 'Content-Type: application/json' \
    --data '{"input_1": "Hello"}'
```

## Worker Utils

### Download a file from url:
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

Install [poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)


Run in development mode:

```bash
poetry install
poetry run maestro-init
```

To bump the package version:

```
poetry version (major|minor|patch)
```
