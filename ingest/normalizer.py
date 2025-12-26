from typing import List

# OpenTelemetry protobuf imports, this class represents the exact message the collector sends.
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest
)

# Everything past this point must only use ExecutionEvent, never OTLP objects.
from ingest.models import ExecutionEvent


# Function to normalize incoming trace data into execution events
# Input → raw bytes (protocol-specific)
# Output → list of Driftline-native events
def normalize_trace_request(payload: bytes) -> List[ExecutionEvent]:

    # Parse the incoming protobuf payload into the ExportTraceServiceRequest object
    req = ExportTraceServiceRequest()
    req.ParseFromString(payload)

    # Convert each span into an ExecutionEvent
    events: List[ExecutionEvent] = []

    # Iterate through ResourceSpans → ScopeSpans → Spans

    # Iterate over the resource spans in the trace request
    # Each resource_span groups: all spans emitted by ONE service instance.
    for rs in req.resource_spans:
        service_name = "unknown"

        for attr in rs.resource.attributes:
            if attr.key == "service.name":
                service_name = attr.value.string_value

        # Iterate over the scope spans within each resource span
        # Each scope_span groups: spans emitted by ONE instrumentation library.
        for scope in rs.scope_spans:

            # Iterate over each span within the scope span
            for span in scope.spans:
                
                # Calculate the duration of the span in milliseconds
                duration_ms = (
                    span.end_time_unix_nano - span.start_time_unix_nano
                ) / 1e6

                # Create an ExecutionEvent for each span
                events.append(
                    ExecutionEvent(
                        service=service_name,
                        trace_id=span.trace_id.hex(),
                        span_id=span.span_id.hex(),
                        parent_span_id=span.parent_span_id.hex() or None,
                        name=span.name,
                        kind=span.kind,
                        duration_ms=round(duration_ms, 2),
                    )
                )
    # Return the list of normalized execution events
    return events
