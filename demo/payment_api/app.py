from fastapi import FastAPI
import time
import os

#Wrap FastAPI so every request is traced automatically.
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# These define: who owns tracing and how spans are created
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# These define: how spans are buffered where they are sent
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

#describe service identity
from opentelemetry.sdk.resources import Resource


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

@app.post("/payments/charge")
def charge():
    time.sleep(0.05)
    return {"status": "charged"}
