from fastapi import APIRouter, HTTPException

from agent.incident_agent import run_incident_agent
from agent.store import get_incident_report, persist_incident_report
from drift.store import get_drift
from ingest.db import get_conn

router = APIRouter(prefix="/agent", tags=["agent"])


def _load_evidence(drift_event_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT baseline_metrics, current_metrics, trace_samples, graph_diff, explanation, created_at
        FROM evidence_packs
        WHERE drift_event_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (drift_event_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


@router.post("/investigate/{drift_event_id}")
def investigate_drift(drift_event_id: str):
    drift_event = get_drift(drift_event_id)
    if not drift_event:
        raise HTTPException(status_code=404, detail="Drift event not found")

    evidence = _load_evidence(drift_event_id)
    report = run_incident_agent(drift_event, evidence)
    persist_incident_report(report)
    return report


@router.get("/report/{drift_event_id}")
def get_report(drift_event_id: str):
    report = get_incident_report(drift_event_id)
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")
    return report
