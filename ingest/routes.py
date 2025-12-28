from fastapi import APIRouter, Request
from ingest.normalizer import normalize_trace_request

router = APIRouter(prefix="/ingest")

# Define endpoint to receive trace data, The OpenTelemetry Collector sends data here
@router.post("/traces/v1/traces")
async def ingest_traces(request: Request):

    # Read raw request body
    payload = await request.body()

    # Normalize the trace data into execution events
    # Each event corresponds to a span in the trace
    events = normalize_trace_request(payload)

    # For demo purposes, just print the events
    print(f"Received {len(events)} execution events")
    for e in events:
        print(e.dict())

    return {"status": "ok", "events": len(events)}
