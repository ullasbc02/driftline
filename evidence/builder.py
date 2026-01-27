from datetime import datetime
from typing import Optional
from evidence.models import EvidencePack
from evidence.trace_sampler import sample_traces, sample_traces_bounded
from evidence.explainer import explain_latency_drift

from evidence.graph_diff import diff_graphs

def build_latency_evidence(
    drift_event_id: str,
    service: str,
    baseline_p95: float,
    current_p95: float,
    baseline_graph: dict,
    current_graph: dict,
    *,
    baseline_captured_at_ms: Optional[int] = None,
):
    """
    Build evidence for a latency drift finding.
    - If baseline_captured_at_ms is provided, sample traces time-bounded around it
      and dedupe per trace_id (max duration per trace).
    - Otherwise, retain previous behavior (recent spans, no dedupe) for compatibility.
    """

    if baseline_captured_at_ms is not None:
        traces_before = sample_traces_bounded(
            service,
            limit=5,
            before_ts=baseline_captured_at_ms,
            dedupe=True,
        )
        traces_after = sample_traces_bounded(
            service,
            limit=5,
            after_ts=baseline_captured_at_ms,
            dedupe=True,
        )
    else:
        traces_before = sample_traces(service)
        traces_after = sample_traces(service)

    graph_diff = diff_graphs(baseline_graph, current_graph)

    explanation = explain_latency_drift(
        service,
        baseline_p95,
        current_p95
    )

    if graph_diff["added_edges"]:
        explanation += (
            f" New dependency edges detected: "
            f"{graph_diff['added_edges']}."
        )

    return EvidencePack(
        drift_event_id=drift_event_id,
        baseline_metrics={"p95_ms": baseline_p95},
        current_metrics={"p95_ms": current_p95},
        trace_samples={
            "baseline": traces_before,
            "current": traces_after
        },
        graph_diff=graph_diff,
        explanation=explanation,
        created_at=datetime.utcnow()
    )
