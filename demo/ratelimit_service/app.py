from fastapi import FastAPI
import time
import os
import requests

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "ratelimit-service",
    "env": os.getenv("ENV", "local")
})

trace.set_tracer_provider(TracerProvider(resource=resource))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            insecure=True
        )
    )
)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

@app.post("/ratelimit/check")
def ratelimit_check():
    # simulate rate-limit logic
    time.sleep(0.01)

    # forward request to fraud-service
    resp = requests.post("http://fraud-service:8001/fraud/check", timeout=2)
    return resp.json()
