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

Driftline answers one question existing tools cannot:

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