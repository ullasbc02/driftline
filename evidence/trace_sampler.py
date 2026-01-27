import redis, json
from typing import List, Optional

r = redis.Redis(host="redis", port=6379, decode_responses=True)

EVENT_STREAM = "driftline:events"

def sample_traces(service: str, limit: int = 5) -> List[dict]:
    """
    Sample recent traces for a given service.
    Backward-compatible behavior: recent spans, no dedup, no time bounds.
    """
    return sample_traces_bounded(service=service, limit=limit, before_ts=None, after_ts=None, dedupe=False, scan_count=200)


def sample_traces_bounded(
    service: str,
    limit: int = 5,
    *,
    before_ts: Optional[int] = None,
    after_ts: Optional[int] = None,
    dedupe: bool = True,
    scan_count: int = 500,
) -> List[dict]:
    """
    Sample traces for a service with optional time bounds and deduplication.

    - before_ts: include only events with observed_at_ms < before_ts
    - after_ts: include only events with observed_at_ms > after_ts
    - dedupe: when True, returns at most one record per trace_id with max duration
    - scan_count: how many stream entries to scan from newest
    """
    entries = r.xrevrange(EVENT_STREAM, count=scan_count)

    collected = []
    for _, fields in entries:
        try:
            event = json.loads(fields["event"])  # event_json stored under 'event'
        except Exception:
            continue

        if event.get("service") != service:
            continue

        ts = event.get("observed_at_ms")
        if ts is None:
            continue

        if before_ts is not None and ts >= before_ts:
            continue
        if after_ts is not None and ts <= after_ts:
            continue

        collected.append({
            "trace_id": event.get("trace_id"),
            "duration_ms": float(event.get("duration_ms", 0.0)),
            "observed_at_ms": ts,
        })

        if not dedupe and len(collected) >= limit:
            break

    if dedupe:
        # Keep the max duration per trace_id (one row per trace)
        best: dict[str, dict] = {}
        for ev in collected:
            tid = ev.get("trace_id")
            if not tid:
                continue
            prev = best.get(tid)
            if prev is None or ev["duration_ms"] > prev["duration_ms"]:
                best[tid] = {"trace_id": tid, "duration_ms": ev["duration_ms"]}
        samples = list(best.values())
    else:
        samples = [{"trace_id": ev["trace_id"], "duration_ms": ev["duration_ms"]} for ev in collected]

    return samples[:limit]
