import os
import json
import redis
from ingest.models import ExecutionEvent

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_KEY = os.getenv("DRIFTLINE_STREAM_KEY", "driftline:events")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def publish(event: ExecutionEvent) -> str:
    # Redis Streams values must be flat key/value strings
    payload = event.model_dump()
    payload["event_json"] = json.dumps(payload)  # convenient single field
    return r.xadd(STREAM_KEY, {"event": payload["event_json"]})
