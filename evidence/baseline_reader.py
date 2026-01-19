from ingest.db import get_conn

def load_baseline_metrics(baseline_id: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT profiles_snapshot
        FROM baselines
        WHERE id = %s
        """,
        (baseline_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError("Baseline not found")

    return row["profiles_snapshot"]
