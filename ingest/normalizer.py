from typing import List, Any, Dict
import time

# OpenTelemetry protobuf imports, this class represents the exact message the collector sends.
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest
)

# Everything past this point must only use ExecutionEvent, never OTLP objects.
from ingest.models import ExecutionEvent


def _attr_value(v) -> Any:
    # OTEL AnyValue has multiple oneof fields; check in priority order
    if v.string_value:
        return v.string_value
    if v.int_value:
        return v.int_value
    if v.double_value:
        return v.double_value
    if v.bool_value:
        return v.bool_value
    # arrays/maps ignored for MVP
    return None

def _span_attrs(span) -> Dict[str, Any]:
    out = {}
    for a in span.attributes:
        out[a.key] = _attr_value(a.value)
    return out

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
        env = "unknown"

        for attr in rs.resource.attributes:
            if attr.key == "service.name":
                service_name = attr.value.string_value
            if attr.key == "env":
                env = attr.value.string_value

        # Iterate over the scope spans within each resource span
        # Each scope_span groups: spans emitted by ONE instrumentation library.
        for scope in rs.scope_spans:

            # Iterate over each span within the scope span
            for span in scope.spans:
                
                # Calculate the duration of the span in milliseconds
                duration_ms = (span.end_time_unix_nano - span.start_time_unix_nano) / 1e6
                attrs = _span_attrs(span)

                http_method = attrs.get("http.method")
                http_route = (
                    attrs.get("http.route")
                    or attrs.get("http.target")
                    or attrs.get("url.path")
                )
                status = attrs.get("http.status_code")
                # Create an ExecutionEvent for each span
                events.append(
                    ExecutionEvent(
                        service=service_name,
                        env=env,
                        trace_id=span.trace_id.hex(),
                        span_id=span.span_id.hex(),
                        parent_span_id=span.parent_span_id.hex() or None,
                        name=span.name,
                        kind=span.kind,
                        duration_ms=round(duration_ms, 2),

                        observed_at_ms=int(time.time() * 1000),

                        http_method=http_method,
                        http_route=http_route,
                        http_status_code=int(status) if status is not None else None,
                        attributes=attrs,
                    )
                )
    # Return the list of normalized execution events
    return events
