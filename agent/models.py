from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class DeploymentContext(BaseModel):
    provider: str
    commit_sha: str
    commit_message: str
    author: str
    deployed_at: str
    changed_files: List[str]
    summary: str


class RemediationDecision(BaseModel):
    action: str
    recommendation: str
    rationale: str


class SlackNotification(BaseModel):
    status: str
    channel: str
    message: str
    delivered: bool
    error: Optional[str] = None


class IncidentReport(BaseModel):
    drift_event_id: str
    env: str
    service: str
    drift_types: List[str]
    severity: int
    confidence: float
    root_cause: str
    deployment_context: DeploymentContext
    evidence_summary: Dict[str, Any]
    decision: RemediationDecision
    slack: SlackNotification
    report_markdown: str
