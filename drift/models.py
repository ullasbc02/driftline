from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class DriftFinding(BaseModel):
    drift_type: str                # "path_drift" | "latency_drift" | "error_drift"
    subject: str                   # e.g. "edge payments-api->fraud-service" or "endpoint POST /payments/charge"
    severity: int                  # 1-100
    baseline: Dict[str, Any]
    current: Dict[str, Any]
    explanation: str

class DriftEvent(BaseModel):
    id: str
    env: str
    created_at_ms: int
    baseline_captured_at_ms: int
    findings: List[DriftFinding]
    summary: str
