import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://driftline:driftline@postgres:5432/driftline"
)

def get_conn():
    """Get a database connection with RealDictCursor for dict-like row access."""
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def init_schema():
    """
    Create tables if they don't exist.
    Call this once at startup or via migration.
    """
    conn = get_conn()
    cur = conn.cursor()

    # UUID extension
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Baselines table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS baselines (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            env TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            graph_snapshot JSONB NOT NULL,
            profiles_snapshot JSONB NOT NULL
        )
    """)

    # Drift events table
    cur.execute("""
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
        )
    """)

    # Evidence packs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evidence_packs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            drift_event_id UUID REFERENCES drift_events(id),
            baseline_metrics JSONB NOT NULL,
            current_metrics JSONB NOT NULL,
            trace_samples JSONB NOT NULL,
            explanation TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
