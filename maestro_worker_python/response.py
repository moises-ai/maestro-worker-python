from typing import Any

from pydantic import BaseModel


class WorkerResponse(BaseModel):
    billable_seconds: float | None
    stats: dict[str, float]
    result: dict[str, Any]
    # Opaque passthrough for the deployment; other undeclared fields are dropped.
    internal: dict[str, Any] | None = None


class ValidationError(Exception):
    def __init__(self, reason):
        self.reason = reason
