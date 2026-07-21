# syntax=docker/dockerfile:1

ARG BASE_IMAGE=python:3.12-slim-trixie
FROM ${BASE_IMAGE}

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /bin/

ENV UV_LINK_MODE=copy

WORKDIR /worker

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    PYTHON_BIN="$(uv python find --no-project --no-python-downloads)" \
    && UV_PROJECT_ENVIRONMENT="$("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_config_var("prefix"))')" \
        uv sync --locked --no-dev --no-install-project --inexact \
            --python "$PYTHON_BIN" --no-python-downloads

COPY . .

CMD ["maestro-server", "--worker", "/worker/worker.py", "--port", "8000"]
