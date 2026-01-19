from fastapi import APIRouter, HTTPException, Query
from ingest.db import get_conn
import json

router = APIRouter(prefix="/evidence", tags=["evidence"])

@router.get("/get")
def get_evidence(drift_event_id: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM evidence_packs
        WHERE drift_event_id = %s
        """,
        (drift_event_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")

    return row
