from fastapi import FastAPI
import time
import os
import random

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Service identity
resource = Resource.create({
    "service.name": "fraud-service",
    "env": os.getenv("ENV", "local")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
    insecure=True
)

span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Silent runtime toggle via env var
ENABLE_SLOW_FRAUD = os.getenv("ENABLE_SLOW_FRAUD", "false").lower() == "true"

@app.post("/fraud/check")
def fraud_check():
    # normal behavior
    time.sleep(0.02)

    # silent regression triggered by feature flag / env
    if ENABLE_SLOW_FRAUD:
        time.sleep(random.uniform(0.2, 0.35))

    return {"fraud_score": round(random.random(), 2)}
