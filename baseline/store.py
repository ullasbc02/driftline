import json
import time
import redis
from typing import Dict, Any, List

REDIS_HOST = "redis"
REDIS_PORT = 6379

BASELINE_KEY_PREFIX = "driftline:baseline"
PROFILE_PREFIX = "driftline:profiles"
GRAPH_PREFIX = "driftline:graph"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _latest_profile_keys(env: str) -> List[str]:
    """
    Fetch latest profile keys for an env.
    We assume profiles are keyed by window_start_ms.
    """
    keys = r.keys(f"{PROFILE_PREFIX}:{env}:*")
    if not keys:
        return []

    # group by endpoint and pick latest window per endpoint
    latest = {}
    for k in keys:
        parts = k.split(":")
        window = int(parts[-1])
        endpoint_id = ":".join(parts[:-1])
        if endpoint_id not in latest or window > latest[endpoint_id][0]:
            latest[endpoint_id] = (window, k)

    return [v[1] for v in latest.values()]


def _latest_graph_snapshot(env: str) -> Dict[str, Any]:
    """
    Fetch latest graph nodes + edges snapshot for env.
    """
    node_keys = r.keys(f"{GRAPH_PREFIX}:nodes:{env}:*")
    edge_keys = r.keys(f"{GRAPH_PREFIX}:edges:{env}:*")

    if not node_keys or not edge_keys:
        return {"nodes": [], "edges": []}

    # pick latest window
    latest_node_key = max(node_keys, key=lambda k: int(k.split(":")[-1]))
    latest_edge_key = max(edge_keys, key=lambda k: int(k.split(":")[-1]))

    return {
        "nodes": json.loads(r.get(latest_node_key)),
        "edges": json.loads(r.get(latest_edge_key)),
    }


def create_baseline(env: str) -> Dict[str, Any]:
    """
    Capture current behavior as baseline.
    """
    profiles = []
    for k in _latest_profile_keys(env):
        profiles.append(json.loads(r.get(k)))

    graph = _latest_graph_snapshot(env)

    baseline = {
        "env": env,
        "captured_at": int(time.time() * 1000),
        "profiles": profiles,
        "graph": graph,
    }

    r.set(f"{BASELINE_KEY_PREFIX}:{env}", json.dumps(baseline))
    return baseline


def get_baseline(env: str) -> Dict[str, Any] | None:
    raw = r.get(f"{BASELINE_KEY_PREFIX}:{env}")
    return json.loads(raw) if raw else None
