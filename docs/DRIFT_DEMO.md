# Drift Demo (Incident Commander)

Use these commands to capture a clean baseline, induce path and latency drift, then run the Driftline incident agent.

## Baseline
- Ensure `payment-api` has `USE_RATE_LIMIT=false` in docker-compose.yml.
- Ensure `fraud-service` has `ENABLE_SLOW_FRAUD=false` in docker-compose.yml.

```bash
docker-compose up -d --build

for i in {1..30}; do
  curl -X POST http://localhost:8000/payments/charge >/dev/null
  sleep 1
done

sleep 70
curl -X POST "http://localhost:9000/baseline/set?env=local"
```

## Induce Drift
- Set `USE_RATE_LIMIT=true` for `payment-api` in docker-compose.yml.
- Set `ENABLE_SLOW_FRAUD=true` for `fraud-service` in docker-compose.yml.
- Recreate both services.

```bash
docker-compose up -d --build --force-recreate payment-api fraud-service
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
curl -X POST "http://localhost:9000/agent/investigate/<ID_FROM_LIST>"
curl "http://localhost:9000/agent/report/<ID_FROM_LIST>"
```

Endpoints are exposed on port 9000: `/baseline/*`, `/drift/*`, `/evidence/*`, and `/agent/*`.
