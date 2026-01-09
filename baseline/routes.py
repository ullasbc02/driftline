from fastapi import APIRouter, HTTPException, Query
from baseline.store import create_baseline, get_baseline

router = APIRouter(prefix="/baseline", tags=["baseline"])


@router.post("/set")
def set_baseline(env: str = Query(...)):
    baseline = create_baseline(env)
    if not baseline["profiles"] and not baseline["graph"]["nodes"]:
        raise HTTPException(
            status_code=400,
            detail="No profiles or graph data available to baseline yet"
        )

    return {
        "status": "baseline_set",
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
