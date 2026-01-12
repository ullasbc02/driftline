import json
import time
import redis
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List

from baseline.store import get_baseline  # uses Redis baseline JSON
from drift.diff import diff_baseline_vs_current
from drift.store import create_drift_event, list_drift_ids, get_drift

REDIS_HOST = "redis"
REDIS_PORT = 6379
PROFILE_PREFIX = "driftline:profiles"
GRAPH_PREFIX = "driftline:graph"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

router = APIRouter(prefix="/drift", tags=["drift"])

def _latest_profile_keys(env: str) -> List[str]:
    keys = r.keys(f"{PROFILE_PREFIX}:{env}:*")
    if not keys:
        return []
    latest = {}
    for k in keys:
        parts = k.split(":")
        window = int(parts[-1])
        endpoint_id = ":".join(parts[:-1])
        if endpoint_id not in latest or window > latest[endpoint_id][0]:
            latest[endpoint_id] = (window, k)
    return [v[1] for v in latest.values()]

def _latest_graph(env: str) -> Dict[str, Any]:
    node_keys = r.keys(f"{GRAPH_PREFIX}:nodes:{env}:*")
    edge_keys = r.keys(f"{GRAPH_PREFIX}:edges:{env}:*")
    if not node_keys or not edge_keys:
        return {"nodes": [], "edges": []}
    latest_node_key = max(node_keys, key=lambda k: int(k.split(":")[-1]))
    latest_edge_key = max(edge_keys, key=lambda k: int(k.split(":")[-1]))
    return {
        "nodes": json.loads(r.get(latest_node_key)),
        "edges": json.loads(r.get(latest_edge_key)),
    }

def _current_snapshot(env: str) -> Dict[str, Any]:
    profiles = []
    for k in _latest_profile_keys(env):
        profiles.append(json.loads(r.get(k)))
    graph = _latest_graph(env)
    return {
        "env": env,
        "captured_at": int(time.time() * 1000),
        "profiles": profiles,
        "graph": graph,
    }

@router.post("/check")
def check_drift(env: str = Query(...)):
    baseline = get_baseline(env)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found. Set it first via /baseline/set")

    current = _current_snapshot(env)
    if not current["profiles"] and not current["graph"]["nodes"]:
        raise HTTPException(
            status_code=400,
            detail="No current profiles/graph available yet. Wait for window flush and retry."
        )

    findings = diff_baseline_vs_current(baseline, current)
    if not findings:
        return {
            "status": "no_drift",
            "env": env,
            "baseline_captured_at": baseline.get("captured_at"),
            "current_captured_at": current.get("captured_at"),
        }

    # build drift event payload
    payload = {
        "env": env,
        "created_at_ms": int(time.time() * 1000),
        "baseline_captured_at_ms": int(baseline.get("captured_at", 0)),
        "findings": [f.model_dump() for f in findings],
        "summary": f"{len(findings)} drift finding(s) detected",
    }

    drift = create_drift_event(payload)
    return {
        "status": "drift_detected",
        "drift_id": drift.id,
        "env": env,
        "findings": len(drift.findings),
        "summary": drift.summary,
    }

@router.get("/list")
def list_drifts(env: str = Query(...), limit: int = Query(20, ge=1, le=200)):
    ids = list_drift_ids(env, limit=limit)
    return {"env": env, "count": len(ids), "drift_ids": ids}

@router.get("/get")
def get_drift_api(drift_id: str = Query(...)):
    d = get_drift(drift_id)
    if not d:
        raise HTTPException(status_code=404, detail="Drift event not found")
    return d
