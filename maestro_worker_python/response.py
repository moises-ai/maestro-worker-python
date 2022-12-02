from typing import Dict, Optional
from pydantic import BaseModel

class WorkerResponse(BaseModel):
    billable_seconds: Optional[int] = ...
    stats: Dict[str, float]
    result: Dict


class ValidationError(Exception):
    def __init__(self, reason):
        self.reason = reason
