# Driftline

**Autonomous DevOps incident commander for behavioral drift in distributed systems.**

Driftline sits on top of OpenTelemetry traces and answers a question traditional observability tools don’t:

> **What changed in production compared to when things were known to be good — and why?**

---

##  The Problem

Modern systems fail in subtle ways:

* Feature flags flip
* Dependencies change
* Rate limits appear
* Infrastructure config drifts

Often:

* Nothing crashes
* Metrics look “mostly fine”
* But behavior is *different*

Existing observability tools show **symptoms** (latency, errors),
but not **what changed**.

---

##  The Solution

Driftline introduces **behavioral baselines**.

You explicitly capture a known-good snapshot of:

* execution paths (service → service)
* endpoint latency profiles
* status/error distributions

Driftline then:

* continuously compares current behavior to the baseline
* detects **path drift**, **latency drift**, and **error drift**
* produces a **stored evidence pack** explaining the change
* runs an **incident agent** that investigates root cause, recommends remediation, notifies Slack, and generates an audit-ready report

---

##  Incident Commander Workflow

```
Detect drift
   ↓
Investigate root cause
   ↓
Decide action
   ↓
Create fix / rollback recommendation
   ↓
Notify team
   ↓
Generate incident report
```

The hackathon agent is exposed at:

```bash
curl -X POST "http://localhost:9000/agent/investigate/<DRIFT_ID>"
curl "http://localhost:9000/agent/report/<DRIFT_ID>"
```

If `SLACK_WEBHOOK_URL` is set, Driftline posts to Slack. Without it, the notification is mocked and stored with the incident report for demos.

---

##  What Driftline Detects

### 1. Path Drift (Structural Change)

```
Baseline:
payments-api → fraud-service

Current:
payments-api → ratelimit-service → fraud-service
```

Detected even if latency is acceptable.

---

### 2. Latency Drift

* p95 / p99 regression
* absolute + relative thresholds

---

### 3. Error Drift

* new 429 / 5xx
* distribution changes

---

##  Evidence Packs (Why Driftline Is Trustworthy)

Every drift event includes:

* baseline vs current metrics
* execution graph diff
* sampled traces responsible for the drift
* human-readable explanation

Drift is **replayable, inspectable, and provable**.

---

##  Architecture Overview

```
Services (OpenTelemetry)
        ↓
OTEL Collector
        ↓
Driftline Ingest API
        ↓
Normalizer → Execution Events
        ↓
Profiler (latency + status)
        ↓
Graph Builder (nodes + edges)
        ↓
Baseline Snapshot
        ↓
Diff Engine
        ↓
Drift Event + Evidence Pack
        ↓
Incident Agent
        ↓
Slack Alert + Markdown Incident Report
```

---

##  Tech Stack

* **Instrumentation:** OpenTelemetry
* **Collector:** OpenTelemetry Collector
* **Backend:** Python + FastAPI
* **Data Store:** PostgreSQL (JSONB)
* **Execution Graph:** Nodes + Edges tables
* **Infra:** Docker Compose

---

##  End-to-End Run And Verification

This is the full flow to run Driftline from scratch and verify path drift detection.

### Prerequisites

* Docker + Docker Compose installed
* `curl` installed
* `jq` installed (optional but recommended)

### 1. Clean Start

```bash
docker-compose down -v
docker-compose up --build -d
```

Check services:

```bash
docker-compose ps
```

You should see these services running:

* `payment-api`
* `fraud-service`
* `ratelimit-service`
* `driftline-ingest`
* `graph-builder`
* `profiler`
* `redis`
* `postgres`
* `otel-collector`

### 2. Initialize DB Schema

Run once after a fresh volume reset:

```bash
cat db-init.sql | docker exec -i driftline-postgres-1 psql -U driftline -d driftline
```

Verify tables:

```bash
docker exec driftline-postgres-1 psql -U driftline -d driftline -c "\\dt"
```

Expected tables:

* `baselines`
* `drift_events`
* `evidence_packs`

### 3. Generate Baseline Traffic

With `USE_RATE_LIMIT=true` in `docker-compose.yml`, traffic path is:

`payments-api -> ratelimit-service -> fraud-service`

```bash
for i in {1..20}; do
        curl -s -X POST http://localhost:8000/payments/charge >/dev/null
        sleep 0.4
done
```

Important timing note:

* `GRAPH` consumer uses `TRACE_TTL_SEC=120`
* Wait long enough for trace assembly + window flush

```bash
sleep 150
```

### 4. Capture Baseline

```bash
curl -s -X POST "http://localhost:9000/baseline/set?env=local" | jq .
```

Verify baseline graph:

```bash
curl -s "http://localhost:9000/baseline/get?env=local" | jq '.graph'
```

Expected:

* `nodes` includes `payments-api`, `ratelimit-service`, `fraud-service`
* `edges` includes `payments-api -> ratelimit-service`
* `edges` includes `ratelimit-service -> fraud-service`

### 5. Introduce Path Change

Edit `docker-compose.yml`:

* Change `payment-api` env from `USE_RATE_LIMIT=true`
* To `USE_RATE_LIMIT=false`

Recreate only `payment-api`:

```bash
docker-compose up -d --build --force-recreate payment-api
```

Now path becomes:

`payments-api -> fraud-service`

### 6. Generate Current Traffic (After Change)

```bash
for i in {1..20}; do
        curl -s -X POST http://localhost:8000/payments/charge >/dev/null
        sleep 0.4
done
sleep 150
```

### 7. Run Drift Detection

```bash
curl -s -X POST "http://localhost:9000/drift/check?env=local" | jq .
```

Expected:

* `status` is `drift_detected`
* You get a `drift_id`

### 8. Inspect Drift Event

```bash
DRIFT_ID=$(curl -s -X POST "http://localhost:9000/drift/check?env=local" | jq -r '.drift_id')
curl -s "http://localhost:9000/drift/get?drift_id=$DRIFT_ID" | jq .
```

Expected `path_drift` findings include:

* Added edge: `payments-api -> fraud-service`
* Removed edge: `payments-api -> ratelimit-service`
* Removed edge: `ratelimit-service -> fraud-service`

### 9. Optional: Check Drift List And Evidence

```bash
curl -s "http://localhost:9000/drift/list?env=local" | jq .
curl -s "http://localhost:9000/evidence/get?drift_event_id=$DRIFT_ID" | jq .
```

### 10. Reset Back To Original Demo Path

Set `USE_RATE_LIMIT=true` again and recreate `payment-api`:

```bash
docker-compose up -d --build --force-recreate payment-api
```

##  Quick Troubleshooting

* Baseline returns `edges: 0`.
Cause: not enough wait time for graph finalization.
Fix: wait at least `TRACE_TTL_SEC + flush margin` (use `sleep 150`).

* `Internal Server Error` on `/baseline/set`.
Cause: DB schema not initialized.
Fix: run step 2 (`db-init.sql`).

* `payments/charge` fails with DNS error for `ratelimit-service`.
Cause: service not up.
Fix: run `docker-compose ps` and restart stack.

---

##  Why Driftline Is Different

| Traditional Observability | Driftline                    |
| ------------------------- | ---------------------------- |
| Metrics & alerts          | Behavioral comparison        |
| Anomaly guessing          | Explicit baselines           |
| Raw traces                | Structured evidence          |
| “Something is slow”       | “This changed, here’s proof” |

---

##  MVP Scope

**Built**

* Explicit baselines
* Execution graph snapshots
* Path drift detection
* Latency drift detection
* Evidence packs

**Intentionally postponed**

* ML diagnosis
* Auto remediation
* Multi-tenant SaaS
* Billing & auth

---

##  Status

Driftline is an early-stage MVP designed to demonstrate:

* a new abstraction over traces
* a developer-first debugging workflow
* a strong foundation for expansion

---

##  Contact

Built by **Ullas**
Open to feedback and collaboration.
