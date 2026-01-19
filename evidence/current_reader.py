import redis, json

r = redis.Redis(host="redis", port=6379, decode_responses=True)

PROFILE_PREFIX = "driftline:profiles"

def load_current_profiles(env: str):
    keys = r.keys(f"{PROFILE_PREFIX}:{env}:*")
    latest = {}

    for k in keys:
        parts = k.split(":")
        window = int(parts[-1])
        endpoint_id = ":".join(parts[:-1])

        if endpoint_id not in latest or window > latest[endpoint_id][0]:
            latest[endpoint_id] = (window, k)

    return [json.loads(r.get(v[1])) for v in latest.values()]
