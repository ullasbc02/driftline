from fastapi import FastAPI
from ingest.routes import router

app = FastAPI(title="Driftline Ingest")

app.include_router(router)
