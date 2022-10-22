# Moises Worker Utils

This module simplifies the creation of a standard inference worker to run on the Maestro infra-structure.

## Installation
To install latest:
```
pip install git+ssh://git@github.com/moises-ai/maestro-worker-utils.git
```

To install a specific version:
```
pip install git+ssh://git@github.com/moises-ai/maestro-worker-utils.git@1.0.13
```

## Setup
Create a `worker.py` file with a `MoisesWorker` class, as the example below. The class must initialize the model and expose an inference function.

``` python
import logging
import traceback

def your_model(input):
    return f"{input} World"

class MoisesWorker(object):
    def __init__(self):
        print("Loading model...")
        self.model = your_model
        print("Model loaded")

    def inference(self, input_data):
        try:
            input_example = input_data.get("input_1", "Hello")
            return self.model(input_example)
        except Exception as e:
            tb = traceback.format_exc()
            logging.exception(e)
            return {"error": str(tb)}
        finally:
            logging.info("cleaning up")
```

## Testing your worker

### Using `maestro-cli`:

Run the CLI passing your worker file as the first param, then, any parameters exposed by your class. In this example, `input_1` will be sent to your worker, with the value `Hello`.

```bash
maestro-cli ./worker.py --input_1 Hello
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

## Dockerizing your worker

### Setup

Make sure to add a `requirements.txt` that includes the last version of this package as well as your dependencies.
```
git+ssh://git@github.com/moises-ai/maestro-worker-utils.git@1.0.13
```

Create a `Dockerfile` and Make sure to:
- Install CUDA if GPU inference is needed
- Install everything needed by your worker
- Include the model in the docker image

Example:
```DockerFile
FROM [your base image]
# You may have the model on your machine for testing using docker-compose
# Don't commit the model to the repo and download it from storage during CI
# A Github actions example is given later on the Deployment section
COPY ./models /worker/models
WORKDIR /worker
COPY ./requirements.txt /worker/requirements.txt
RUN pip3 install -r requirements.txt
COPY ./ /worker
ENTRYPOINT maestro-server --worker /worker/worker.py --base_path /worker-example --port 8000
```
### Testing with docker-compose

To test locally, use docker-compose, here is a `docker-compose.yaml` example:

```yaml
version: "3.9"
services:
  app:
    build: .
    command: moises-server --worker /worker/worker.py --base_path /worker-example --port 8000 --reload --debug
    ports:
      - "8000:8000"
    expose:
      - "8000"
    volumes:
      - ./:/worker/

```

Use `docker-compose build --ssh default` to build, then run with `docker-compose run --service-ports app`

The http server will run on port `8000` and you can test a request using curl:
```bash
curl --request POST --url http://localhost:8000/worker-example/inference  --header 'Content-Type: application/json' \
    --data '{"input_1": "Hello"}'
```

You can also test via CLI, using:

```bash
docker-compose run app maestro-cli /worker/worker --input_1 Hello
```