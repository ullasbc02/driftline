import os, json, time
import redis
from collections import defaultdict
from typing import Dict, Tuple, List, Optional

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

EVENT_STREAM = os.getenv("DRIFTLINE_STREAM_KEY", "driftline:events")
GRAPH_PREFIX = os.getenv("DRIFTLINE_GRAPH_PREFIX", "driftline:graph")

GROUP = os.getenv("DRIFTLINE_GRAPH_GROUP", "graph-group")
CONSUMER = os.getenv("CONSUMER_NAME", "graph-1")

WINDOW_SEC = int(os.getenv("GRAPH_WINDOW_SEC", "60"))
TRACE_TTL_SEC = int(os.getenv("TRACE_TTL_SEC", "120"))  # how long to wait to assemble spans for a trace
MAX_EDGE_SAMPLES = int(os.getenv("EDGE_LAT_SAMPLE_SIZE", "400"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def ensure_group():
    try:
        r.xgroup_create(EVENT_STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

def window_start_ms(ts_ms: int) -> int:
    w = WINDOW_SEC * 1000
    return (ts_ms // w) * w

def quantile(sorted_vals: List[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    idx = int(q * (len(sorted_vals) - 1))
    return float(sorted_vals[idx])

def edge_key(env: str, wstart: int) -> str:
    return f"{GRAPH_PREFIX}:edges:{env}:{wstart}"

def node_key(env: str, wstart: int) -> str:
    return f"{GRAPH_PREFIX}:nodes:{env}:{wstart}"

class TraceBuffer:
    """
    In-memory trace assembly.
    Stores span_id -> (service, parent_span_id, duration_ms)
    """
    def __init__(self):
        self.spans: Dict[str, Tuple[str, Optional[str], float]] = {}
        self.first_seen_ms: int = int(time.time() * 1000)
        self.last_seen_ms: int = self.first_seen_ms
        self.env: str = "unknown"

    def add_span(self, env: str, span_id: str, service: str, parent_span_id: Optional[str], duration_ms: float):
        self.env = env
        self.spans[span_id] = (service, parent_span_id, duration_ms)
        now = int(time.time() * 1000)
        self.last_seen_ms = now

def run():
    ensure_group()
    print("Graph builder consumer running...")

    # trace_id -> TraceBuffer
    traces: Dict[str, TraceBuffer] = {}

    # rolling aggregates per (env, window_start, from_service, to_service)
    edge_counts: Dict[Tuple[str, int, str, str], int] = defaultdict(int)
    edge_lat_samples: Dict[Tuple[str, int, str, str], List[float]] = defaultdict(list)
    nodes_seen: Dict[Tuple[str, int], set] = defaultdict(set)

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
                    trace_id = event.get("trace_id")
                    span_id = event.get("span_id")
                    parent_span_id = event.get("parent_span_id")
                    dur = float(event.get("duration_ms", 0.0))
                    ts = int(event.get("observed_at_ms", now_ms))

                    if not trace_id or not span_id:
                        r.xack(EVENT_STREAM, GROUP, msg_id)
                        continue

                    tb = traces.get(trace_id)
                    if tb is None:
                        tb = TraceBuffer()
                        traces[trace_id] = tb

                    tb.add_span(env, span_id, service, parent_span_id, dur)

                    # we also track nodes immediately per time window
                    wstart = window_start_ms(ts)
                    nodes_seen[(env, wstart)].add(service)

                    r.xack(EVENT_STREAM, GROUP, msg_id)

        # periodically finalize traces and flush closed windows
        if time.time() - last_flush_check > 2:
            last_flush_check = time.time()

            # 1) Finalize traces that are "old enough"
            cutoff_ms = now_ms - (TRACE_TTL_SEC * 1000)
            done_trace_ids = [tid for tid, tb in traces.items() if tb.last_seen_ms < cutoff_ms]

            for tid in done_trace_ids:
                tb = traces[tid]

                # Build cross-service edges from assembled trace
                # For each span, if parent exists, compare parent.service vs child.service.
                for child_span_id, (child_service, parent_id, child_dur) in tb.spans.items():
                    if not parent_id:
                        continue
                    parent = tb.spans.get(parent_id)
                    if not parent:
                        continue
                    parent_service = parent[0]

                    if parent_service != child_service:
                        # edge exists: parent_service -> child_service
                        # Use child's observed time window approximated by tb.last_seen_ms
                        wstart = window_start_ms(tb.last_seen_ms)
                        k = (tb.env, wstart, parent_service, child_service)
                        edge_counts[k] += 1

                        # store sample for p95/p99 of child duration (proxy for call time)
                        samples = edge_lat_samples[k]
                        if len(samples) < MAX_EDGE_SAMPLES:
                            samples.append(child_dur)
                        else:
                            j = int(time.time_ns() % MAX_EDGE_SAMPLES)
                            samples[j] = child_dur

                        nodes_seen[(tb.env, wstart)].add(parent_service)
                        nodes_seen[(tb.env, wstart)].add(child_service)

                del traces[tid]

            # 2) Flush windows that are definitely closed (older than current window)
            current_wstart = window_start_ms(now_ms)
            flush_env_windows = [(env, w) for (env, w) in nodes_seen.keys() if w < current_wstart]

            for env, wstart in flush_env_windows:
                # Nodes snapshot
                nkey = node_key(env, wstart)
                r.set(nkey, json.dumps(sorted(list(nodes_seen[(env, wstart)]))))
                r.expire(nkey, 60 * 60 * 6)

                # Edges snapshot
                edges_out = []
                for (e, ws, frm, to), cnt in list(edge_counts.items()):
                    if e == env and ws == wstart:
                        s = sorted(edge_lat_samples[(e, ws, frm, to)])
                        edges_out.append({
                            "from": frm,
                            "to": to,
                            "count": cnt,
                            "p50_ms": quantile(s, 0.50),
                            "p95_ms": quantile(s, 0.95),
                            "p99_ms": quantile(s, 0.99),
                        })
                        # cleanup flushed buckets
                        del edge_counts[(e, ws, frm, to)]
                        del edge_lat_samples[(e, ws, frm, to)]

                ekey = edge_key(env, wstart)
                r.set(ekey, json.dumps(edges_out))
                r.expire(ekey, 60 * 60 * 6)

                # cleanup nodes
                del nodes_seen[(env, wstart)]

if __name__ == "__main__":
    run()
