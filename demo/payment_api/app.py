from fastapi import FastAPI
import time
import os
import requests
#Wrap FastAPI so every request is traced automatically.
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# These define: who owns tracing and how spans are created
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# These define: how spans are buffered where they are sent
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

#describe service identity
from opentelemetry.sdk.resources import Resource

USE_RATE_LIMIT = os.getenv("USE_RATE_LIMIT", "false") == "true"
resource = Resource.create({
    "service.name": "payments-api",
    "env": "local"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
    insecure=True
)


span_processor = BatchSpanProcessor(otlp_exporter)

#Use the OpenTelemetry SDK as the global tracing engine for this app.
trace.get_tracer_provider().add_span_processor(span_processor)

app = FastAPI()

# Whenever FastAPI handles a request, automatically create spans.
FastAPIInstrumentor.instrument_app(app)
# Instrument outgoing HTTP requests to create child spans
RequestsInstrumentor().instrument()

@app.post("/payments/charge")
def charge():
    time.sleep(0.05)

    if USE_RATE_LIMIT:
        resp = requests.post(
            "http://ratelimit-service:8002/ratelimit/check",
            timeout=2
        )
    else:
        resp = requests.post(
            "http://fraud-service:8001/fraud/check",
            timeout=2
        )

    return {"status": "charged", "fraud": resp.json()}