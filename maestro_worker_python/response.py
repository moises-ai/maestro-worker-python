from typing import Any

from pydantic import BaseModel


class WorkerResponse(BaseModel):
    billable_seconds: int | None
    stats: dict[str, float]
    result: dict[str, Any]


class ValidationError(Exception):
    def __init__(self, reason):
        self.reason = reason
