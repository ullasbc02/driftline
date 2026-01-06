import os, json, time
import redis
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Optional, List

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

EVENT_STREAM = os.getenv("DRIFTLINE_STREAM_KEY", "driftline:events")
PROFILE_PREFIX = os.getenv("DRIFTLINE_PROFILE_PREFIX", "driftline:profiles")

GROUP = os.getenv("DRIFTLINE_PROFILE_GROUP", "profiler-group")
CONSUMER = os.getenv("CONSUMER_NAME", "profiler-1")

WINDOW_SEC = int(os.getenv("PROFILE_WINDOW_SEC", "60"))
MAX_SAMPLE = int(os.getenv("LAT_SAMPLE_SIZE", "400"))  # reservoir size

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def ensure_group():
    try:
        r.xgroup_create(EVENT_STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

def quantile(sorted_vals: List[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    idx = int(q * (len(sorted_vals) - 1))
    return float(sorted_vals[idx])

def window_start_ms(ts_ms: int) -> int:
    w = WINDOW_SEC * 1000
    return (ts_ms // w) * w

@dataclass
class EndpointProfile:
    env: str
    service: str
    http_method: str
    http_route: str
    window_start_ms: int
    window_end_ms: int
    count: int
    status_counts: Dict[str, int]
    p50_ms: Optional[float]
    p95_ms: Optional[float]
    p99_ms: Optional[float]

class Bucket:
    def __init__(self):
        self.count = 0
        self.status = Counter()
        self.samples: List[float] = []

    def add(self, duration_ms: float, status_code: Optional[int]):
        self.count += 1

        if status_code is None:
            self.status["unknown"] += 1
        elif 200 <= status_code < 300:
            self.status["2xx"] += 1
        elif 400 <= status_code < 500:
            self.status["4xx"] += 1
        elif 500 <= status_code < 600:
            self.status["5xx"] += 1
        else:
            self.status[str(status_code)] += 1

        # reservoir-ish sampling (simple cap for MVP)
        if len(self.samples) < MAX_SAMPLE:
            self.samples.append(duration_ms)
        else:
            # overwrite random index occasionally (cheap reservoir)
            j = int(time.time_ns() % MAX_SAMPLE)
            self.samples[j] = duration_ms

def profile_key(env: str, service: str, method: str, route: str, wstart: int) -> str:
    # keep key redis-friendly (avoid spaces)
    safe_route = route.replace(" ", "_")
    return f"{PROFILE_PREFIX}:{env}:{service}:{method}:{safe_route}:{wstart}"

def flush_profile(env, service, method, route, wstart, bucket: Bucket):
    s = sorted(bucket.samples)
    wend = wstart + WINDOW_SEC * 1000

    prof = EndpointProfile(
        env=env,
        service=service,
        http_method=method,
        http_route=route,
        window_start_ms=wstart,
        window_end_ms=wend,
        count=bucket.count,
        status_counts=dict(bucket.status),
        p50_ms=quantile(s, 0.50),
        p95_ms=quantile(s, 0.95),
        p99_ms=quantile(s, 0.99),
    )

    key = profile_key(env, service, method, route, wstart)
    r.set(key, json.dumps(asdict(prof)))
    # optional: TTL so Redis doesn’t grow forever in MVP
    r.expire(key, 60 * 60 * 6)  # 6 hours

def run():
    ensure_group()
    print("Profiler consumer running...")

    # buckets keyed by (env, service, method, route, window_start_ms)
    buckets: Dict[Tuple[str, str, str, str, int], Bucket] = defaultdict(Bucket)

    last_flush_check = time.time()

    while True:
        resp = r.xreadgroup(
            GROUP,
            CONSUMER,
            streams={EVENT_STREAM: ">"},
            count=200,
            block=2000
        )

        now_ms = int(time.time() * 1000)

        if resp:
            for _, messages in resp:
                for msg_id, fields in messages:
                    event = json.loads(fields["event"])

                    env = event.get("env", "unknown")
                    service = event.get("service", "unknown")
                    method = event.get("http_method") or "unknown"
                    route = event.get("http_route") or event.get("name") or "unknown"
                    status_code = event.get("http_status_code")
                    dur = float(event.get("duration_ms", 0.0))
                    ts = int(event.get("observed_at_ms", now_ms))

                    wstart = window_start_ms(ts)
                    key = (env, service, method, route, wstart)
                    buckets[key].add(dur, status_code)

                    r.xack(EVENT_STREAM, GROUP, msg_id)

        # flush closed windows periodically
        if time.time() - last_flush_check > 2:
            last_flush_check = time.time()
            current_wstart = window_start_ms(now_ms)

            to_flush = [k for k in buckets.keys() if k[4] < current_wstart]
            for k in to_flush:
                env, service, method, route, wstart = k
                flush_profile(env, service, method, route, wstart, buckets[k])
                del buckets[k]

if __name__ == "__main__":
    run()
