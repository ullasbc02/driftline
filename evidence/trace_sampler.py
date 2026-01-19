import redis, json
from typing import List

r = redis.Redis(host="redis", port=6379, decode_responses=True)

EVENT_STREAM = "driftline:events"

def sample_traces(service: str, limit: int = 5) -> List[dict]:
    """
    Sample recent traces for a given service.
    """
    entries = r.xrevrange(EVENT_STREAM, count=200)
    samples = []

    for _, fields in entries:
        event = json.loads(fields["event"])
        if event.get("service") == service:
            samples.append({
                "trace_id": event["trace_id"],
                "duration_ms": event["duration_ms"]
            })
            if len(samples) >= limit:
                break

    return samples
