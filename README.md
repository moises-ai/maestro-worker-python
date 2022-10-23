# Maestro Worker Python

This module scaffolds the creation of a standard inference worker to run on the Moises/Maestro infra-structure.

## Installation
To install the main branch:
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git
```

To install a version (recommended):
```
pip install git+https://github.com/moises-ai/maestro-worker-python.git@1.0.17
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

## Using Docker Compose

### Build image
```bash
docker-compose build
```

### Run the server

```bash
docker-compose run --service-ports worker
```
