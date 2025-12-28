from pydantic import BaseModel
from typing import Optional

# Data model representing a normalized execution event
class ExecutionEvent(BaseModel):
    service: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]

    name: str
    kind: int

    duration_ms: float
