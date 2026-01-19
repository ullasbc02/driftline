from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

class EvidencePack(BaseModel):
    drift_event_id: str
    baseline_metrics: Dict[str, Any]
    current_metrics: Dict[str, Any]
    trace_samples: Dict[str, List[Dict[str, Any]]]
    graph_diff: Dict[str, Any]      # NEW
    explanation: str
    created_at: datetime

