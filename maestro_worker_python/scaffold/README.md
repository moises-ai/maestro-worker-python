# Maestro worker

## Setup

Install the locked dependencies:

```bash
uv sync
```

Run the worker locally:

```bash
WORKER_VERSION=dev uv run maestro-server --worker worker.py --port 8000 --reload True
```

Build and run it in Docker:

```bash
docker compose build
docker compose up
```

`WORKER_VERSION` identifies the worker artifact in `/health`. Docker Compose
sets it to `dev`; deployments should set it to the exact image tag.

`BASE_IMAGE` must provide a Python interpreter that satisfies the project's
`requires-python` constraint. Its executable may be named `python`, `python3`,
or live in an environment such as Conda; uv discovers it without downloading a
separate interpreter.

## PyTorch workers

Keep the PyTorch version in `pyproject.toml` so local development and the
container resolve the same release:

```toml
dependencies = [
  # Other worker dependencies...
  "torch==<version>",
]
```

PyTorch publishes different artifacts for CPU and CUDA. Configure uv to use a
CPU build outside Linux and the CUDA build chosen for deployment on Linux:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform != 'linux'" },
  { index = "pytorch-cuda", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cuda"
url = "https://download.pytorch.org/whl/<cuda-variant>"
explicit = true
```

Replace `<version>` and `<cuda-variant>` (for example, `cu130`), then run
`uv lock` and commit `uv.lock`. See uv's [PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) for the
available layouts.

The default Docker base installs PyTorch from the lock. To use a PyTorch image
that already contains the GPU stack, select a tag with the same PyTorch and CUDA
versions:

```bash
BASE_IMAGE="pytorch/pytorch:<matching-tag>" docker compose build
```

Docker reuses matching installed packages and installs the remaining locked
dependencies. Use local `uv` commands for the fast development loop, then test
the container for CUDA behavior, native libraries, and performance.
