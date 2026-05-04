from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent.routes import router as agent_router
from ingest.routes import router as ingest_router
from baseline.routes import router as baseline_router
from drift.routes import router as drift_router
from evidence.routes import router as evidence_router

app = FastAPI(title="Driftline Ingest")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(baseline_router)
app.include_router(drift_router)
app.include_router(evidence_router)
app.include_router(agent_router)
