import json
from datetime import datetime
from typing import Optional

from agent.models import IncidentReport
from ingest.db import get_conn


def ensure_incident_schema():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incident_reports (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            drift_event_id TEXT NOT NULL UNIQUE,
            env TEXT NOT NULL,
            service TEXT NOT NULL,
            severity INTEGER NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            root_cause TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            slack_message TEXT NOT NULL,
            report_markdown TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def persist_incident_report(report: IncidentReport):
    ensure_incident_schema()
    payload = report.model_dump(mode="json")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO incident_reports (
            drift_event_id, env, service, severity, confidence, root_cause,
            recommendation, slack_message, report_markdown, payload, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (drift_event_id) DO UPDATE SET
            env = EXCLUDED.env,
            service = EXCLUDED.service,
            severity = EXCLUDED.severity,
            confidence = EXCLUDED.confidence,
            root_cause = EXCLUDED.root_cause,
            recommendation = EXCLUDED.recommendation,
            slack_message = EXCLUDED.slack_message,
            report_markdown = EXCLUDED.report_markdown,
            payload = EXCLUDED.payload,
            created_at = EXCLUDED.created_at
        """,
        (
            report.drift_event_id,
            report.env,
            report.service,
            report.severity,
            report.confidence,
            report.root_cause,
            report.decision.recommendation,
            report.slack.message,
            report.report_markdown,
            json.dumps(payload),
            datetime.utcnow(),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_incident_report(drift_event_id: str) -> Optional[dict]:
    ensure_incident_schema()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT payload
        FROM incident_reports
        WHERE drift_event_id = %s
        """,
        (drift_event_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["payload"] if row else None
