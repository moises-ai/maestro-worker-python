from typing import Any

from pydantic import BaseModel, Field


class WorkerIdentity(BaseModel):
    """Which artifact served a request, as reported by its own deployment."""

    name: str | None = None
    version: str | None = None


class WorkerResponse(BaseModel):
    billable_seconds: float | None
    stats: dict[str, float]
    result: dict[str, Any]
    # Opaque passthrough for the deployment; other undeclared fields are dropped.
    internal: dict[str, Any] | None = None
    # Stamped by the server from deployment settings; worker-set values are overwritten.
    worker: WorkerIdentity = Field(default_factory=WorkerIdentity)


class ValidationError(Exception):
    def __init__(self, reason):
        self.reason = reason
