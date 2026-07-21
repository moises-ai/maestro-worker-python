# syntax=docker/dockerfile:1

ARG BASE_IMAGE=python:3.12-slim-trixie
FROM ${BASE_IMAGE}

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /bin/

ENV UV_LINK_MODE=copy

WORKDIR /worker

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --quiet --locked --no-dev --no-emit-project \
        --output-file=/tmp/requirements.txt \
    && uv pip install --system --no-deps --require-hashes \
        --requirement=/tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY . .

CMD ["maestro-server", "--worker", "/worker/worker.py", "--port", "8000"]
