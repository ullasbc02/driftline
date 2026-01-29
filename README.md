# Driftline

**Detect behavioral drift in distributed systems using explicit baselines and execution graph diffs.**

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

##  Local Demo (3-Minute Flow)

```bash
# Start everything
docker-compose up --build
```

### 1. Generate traffic

```bash
curl -X POST http://localhost:8000/payments/charge
```

### 2. Capture baseline

```bash
curl -X POST "http://localhost:9000/baseline/set?env=local"
```

### 3. Introduce a silent change

Flip a runtime flag (no deploy):

```yaml
USE_RATE_LIMIT=true
```

### 4. Detect drift

```bash
curl -X POST "http://localhost:9000/drift/check?env=local"
```

### 5. View evidence

```bash
curl "http://localhost:9000/evidence/get?drift_event_id=<ID>"
```

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
