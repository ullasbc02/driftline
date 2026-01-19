from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from baseline.store import create_baseline, get_baseline
from ingest.db import get_conn

router = APIRouter(prefix="/baseline", tags=["baseline"])


def persist_baseline_to_db(env: str, graph, profiles) -> str:
    """
    Persist baseline snapshot to Postgres.
    Returns the baseline UUID.
    """
    import json
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO baselines (env, created_at, graph_snapshot, profiles_snapshot)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            env,
            datetime.now(timezone.utc),
            json.dumps(graph),
            json.dumps(profiles)
        )
    )

    baseline_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()

    return str(baseline_id)


@router.post("/set")
def set_baseline(env: str = Query(...)):
    baseline = create_baseline(env)
    if not baseline["profiles"] and not baseline["graph"]["nodes"]:
        raise HTTPException(
            status_code=400,
            detail="No profiles or graph data available to baseline yet"
        )

    # Persist to Postgres
    baseline_id = persist_baseline_to_db(env, baseline["graph"], baseline["profiles"])

    return {
        "status": "baseline_set",
        "baseline_id": baseline_id,
        "env": env,
        "captured_at": baseline["captured_at"],
        "profiles": len(baseline["profiles"]),
        "nodes": len(baseline["graph"]["nodes"]),
        "edges": len(baseline["graph"]["edges"]),
    }


@router.get("/get")
def get_baseline_api(env: str = Query(...)):
    baseline = get_baseline(env)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline
