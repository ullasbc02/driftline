# Driftline

**Driftline** is a behavioral drift detection platform that compares how systems
*actually execute work* across environments (staging vs production) to uncover
latency, error, and execution-path mismatches missed by traditional observability tools.

## Why Driftline Exists

Modern systems fail due to **invisible execution changes**, not broken infrastructure.

- No deploy happened
- No tests failed
- Dashboards are green
- Users still experience outages

Driftline answers one question existing tools cannot

> **Is my system behaving the same way in production as it does in staging?**

## What Driftline Detects

- Execution path drift (new or missing dependencies)
- Latency distribution drift (p95 / p99)
- Error pattern drift (429, 5xx)
- Runtime behavior mismatches across environments

This is **behavior drift**, not config drift.

## How It Works (High Level)

1. Capture real runtime execution using OpenTelemetry
2. Build execution graphs from live traffic
3. Profile endpoint behavior per environment
4. Compare profiles and graphs over time
5. Surface explainable drift with evidence

## MVP Scope

- Two environments (staging + production)
- A small set of critical endpoints
- Deterministic drift detection rules
- Evidence-backed explanations

This repository contains the MVP implementation used to demonstrate
behavioral drift detection in real systems.

## Status

🚧 Early-stage prototype (pre-seed)

## License

MIT

## Repository Structure

```text
driftline/
├── README.md
├── docker-compose.yml
├── .env.example
├── collector/
│   └── otel-collector.yaml
├── ingest/
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   └── normalizer.py
├── profiler/
│   ├── latency_profiles.py
│   ├── status_profiles.py
│   └── aggregator.py
├── graph/
│   ├── builder.py
│   ├── diff.py
│   └── models.py
├── drift_engine/
│   ├── rules.py
│   ├── detector.py
│   └── severity.py
├── evidence/
│   ├── sampler.py
│   └── report.py
├── dashboard/        # optional (React later)
├── demo/
│   ├── payment_api/
│   ├── worker/
│   └── scripts/
└── docs/
    ├── architecture.md
    ├── demo_scenario.md
    └── roadmap.md

```
## Getting Started

### Prerequisites

Docker & Docker Compose (or Docker Desktop) installed and running

Optional: Python 3.11+ if you want to run the demo without Docker

### Setup

To start the demo stack
From the repository root run:

```
docker-compose up --build
```
This will build and start:

- payment-api (FastAPI) on http://localhost:8000
- OpenTelemetry collector (logs exported to console)

To stop and remove containers

```
docker-compose down
```

Other Docker Commands 
```
# View logs for all services
docker-compose logs --no-color --timestamps

# View logs for the payment-api only
docker-compose logs payment-api
```

To test the payment endpoint

```
curl -X POST http://localhost:8000/payments/charge
```
- Expect HTTP 200 and a small JSON/text response from the demo API.
  
To check tracing (OTEL)

- The collector prints traces to its logs.
- After calling the endpoint you should see span log output in the console where compose is running.

Run the demo service locally (without Docker)

Create a virtualenv and install dependencies:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo/payment_api/requirements.txt
python demo/payment_api/app.py
```
This project, **Driftline**, is designed to detect "behavioral drift." In plain English: it watches how your software normally behaves (how fast it is, what steps it takes to finish a task) and alerts you if that behavior suddenly changes.

Here is the step-by-step breakdown of how data travels through the system you've built so far.

---

## 1. The Source: The Payment API

Imagine a customer clicks "Pay." Your `payment-api` handles this.

* **What happens:** Even though the code just says `return {"status": "charged"}`, the **OpenTelemetry SDK** you configured acts like a "black box recorder" on an airplane.
* **The Data:** It records a **Span**. This span contains the service name (`payments-api`), how long it took (), and a unique `trace_id` so we can follow this specific request across different services.

## 2. The Courier: OpenTelemetry Collector

The Payment API doesn't want to spend time processing logs; it wants to get back to handling payments. So, it offloads the data immediately.

* **What happens:** The API sends the raw trace data to the **OpenTelemetry Collector** via the `OTLP_EXPORTER_OTLP_ENDPOINT`.
* **The Collector's Job:** It acts as a middleman. It receives data from many different apps and forwards it to Driftline. In your `docker-compose.yml`, you see it sitting in the middle, listening on ports `4317` and `4318`.

## 3. The Front Door: Driftline Ingest API

Now the data enters the "Driftline Platform" block from your architecture diagram.

* **The Endpoint:** Your FastAPI app in `ingest/main.py` creates a specific URL: `/ingest/traces/v1/traces`.
* **The Arrival:** The Collector sends the data here as a "Protobuf" (a highly compressed binary format that humans can't read, but computers read very fast).

## 4. The Translator: The Normalizer

The raw data from the Collector is messy and deeply nested. Your `ingest/normalizer.py` is the most critical part of the code you've written.

* **The Extraction:** It loops through the complex "ResourceSpans" and "ScopeSpans" sent by OpenTelemetry.
* **Normalization:** It converts that complex data into a simple **`ExecutionEvent`**.
* **Before:** A giant, nested binary blob.
* **After:** A clean Python object that looks like this:
> `{"service": "payments-api", "trace_id": "abc...123", "duration_ms": 50.0, ...}`





## 5. The Output: Console Logging (For Now)

In your current `ingest/routes.py`, the final step is:

```python
print(f"Received {len(events)} execution events")

```

Right now, you are seeing the "Proof of Concept." The data has successfully traveled from a simulated user request, through a collector, been translated by your logic, and is now ready to be analyzed.

---

## Summary of the Flow

| Component | Role | Analogy |
| --- | --- | --- |
| **Payment API** | Generates the data | The person writing a letter |
| **OTEL Collector** | Moves the data | The Mail Truck |
| **Ingest API** | Receives the data | The Mailroom |
| **Normalizer** | Cleans the data | Someone opening the envelope and typing the letter into a database |

---

