# Drift Demo (Quick)

Use these commands to capture a clean baseline, then induce a silent latency change and detect drift.

## Baseline
- Ensure `fraud-service` has `ENABLE_SLOW_FRAUD=false` in docker-compose.yml.

```bash
docker-compose up -d --build fraud-service payment-api driftline-ingest profiler graph-builder

for i in {1..30}; do
  curl -X POST http://localhost:8000/payments/charge >/dev/null
  sleep 1
done

sleep 70
curl -X POST "http://localhost:9000/baseline/set?env=local"
```

## Induce Drift
- Flip the flag to true: set `ENABLE_SLOW_FRAUD=true` for `fraud-service` in docker-compose.yml, then recreate it.

```bash
docker-compose up -d --force-recreate fraud-service
sleep 2

for i in {1..30}; do
  curl -X POST http://localhost:8000/payments/charge >/dev/null
  sleep 1
done

sleep 70
```

## Detect & Inspect
```bash
curl -X POST "http://localhost:9000/drift/check?env=local"
curl "http://localhost:9000/drift/list?env=local"
curl "http://localhost:9000/drift/get?drift_id=<ID_FROM_LIST>"
```

Endpoints are exposed on port 9000: `/baseline/*` and `/drift/*`.
