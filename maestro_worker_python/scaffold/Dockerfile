# syntax=docker/dockerfile:1

FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /worker

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY . .

CMD ["maestro-server", "--worker", "/worker/worker.py", "--port", "8000"]
