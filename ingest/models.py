from pydantic import BaseModel
from typing import Optional, Dict, Any

# Data model representing a normalized execution event
class ExecutionEvent(BaseModel):
    service: str
    env: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]

    name: str
    kind: int

    duration_ms: float

    # for profiling
    observed_at_ms: int

    http_method: Optional[str] = None
    http_route: Optional[str] = None
    http_status_code: Optional[int] = None

    # optional: keep raw attrs for future graph/evidence
    attributes: Dict[str, Any] = {}
