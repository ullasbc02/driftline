from fastapi import FastAPI
from ingest.routes import router as ingest_router
from baseline.routes import router as baseline_router
from drift.routes import router as drift_router

app = FastAPI(title="Driftline Ingest")

app.include_router(ingest_router)
app.include_router(baseline_router)
app.include_router(drift_router)
