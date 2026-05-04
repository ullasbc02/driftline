-- Schema initialization script for Driftline
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    env TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    graph_snapshot JSONB NOT NULL,
    profiles_snapshot JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    env TEXT NOT NULL,
    baseline_id UUID REFERENCES baselines(id),
    drift_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    severity INTEGER NOT NULL,
    summary TEXT NOT NULL,
    findings JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_packs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drift_event_id TEXT NOT NULL,
    baseline_metrics JSONB NOT NULL,
    current_metrics JSONB NOT NULL,
    trace_samples JSONB NOT NULL,
    graph_diff JSONB NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS incident_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drift_event_id TEXT NOT NULL UNIQUE,
    env TEXT NOT NULL,
    service TEXT NOT NULL,
    severity INTEGER NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    root_cause TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    slack_message TEXT NOT NULL,
    report_markdown TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
