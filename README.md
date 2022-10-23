# Maestro Worker Python

This module scaffolds the creation of a standard inference worker to run on the Moises/Maestro infra-structure.

## Installation
To install latest:
```
pip install git+ssh://git@github.com/moises-ai/maestro-worker-python.git
```

To install a specific version:
```
pip install git+ssh://git@github.com/moises-ai/maestro-worker-python.git@1.0.11
```

## Maestro init
Run the init script to scaffold a maestro worker in the current directory. 

To create in a different one, use the flag `--directory`

```bash
maestro-init
```

This will create example files to run a worker:
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

## Develop this module

### Test the module locally
```bash
python3 setup.py develop
```