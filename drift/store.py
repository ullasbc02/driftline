import json
import time
import uuid
import redis
from typing import Dict, Any, List, Optional
from drift.models import DriftEvent

REDIS_HOST = "redis"
REDIS_PORT = 6379

DRIFT_INDEX_PREFIX = "driftline:drifts"   # list of drift IDs per env
DRIFT_KEY_PREFIX = "driftline:drift"      # drift event payload by id

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def create_drift_event(payload: Dict[str, Any]) -> DriftEvent:
    drift_id = str(uuid.uuid4())
    payload["id"] = drift_id
    drift = DriftEvent(**payload)

    r.set(f"{DRIFT_KEY_PREFIX}:{drift_id}", drift.model_dump_json())
    r.lpush(f"{DRIFT_INDEX_PREFIX}:{drift.env}", drift_id)
    # keep latest 200 drift ids per env
    r.ltrim(f"{DRIFT_INDEX_PREFIX}:{drift.env}", 0, 199)
    # optional TTL for drift payloads (keep 7 days)
    r.expire(f"{DRIFT_KEY_PREFIX}:{drift_id}", 60 * 60 * 24 * 7)
    return drift

def list_drift_ids(env: str, limit: int = 20) -> List[str]:
    return r.lrange(f"{DRIFT_INDEX_PREFIX}:{env}", 0, max(0, limit - 1))

def get_drift(drift_id: str) -> Optional[DriftEvent]:
    raw = r.get(f"{DRIFT_KEY_PREFIX}:{drift_id}")
    return DriftEvent.model_validate_json(raw) if raw else None
