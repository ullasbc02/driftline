from ingest.db import get_conn
import json

def persist_evidence(pack):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO evidence_packs
        (id, drift_event_id, baseline_metrics, current_metrics,
         trace_samples, explanation, created_at)
        VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s)
        """,
        (
            pack.drift_event_id,
            json.dumps(pack.baseline_metrics),
            json.dumps(pack.current_metrics),
            json.dumps(pack.trace_samples),
            pack.explanation,
            pack.created_at
        )
    )

    conn.commit()
    cur.close()
    conn.close()
