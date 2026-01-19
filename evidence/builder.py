from datetime import datetime
from evidence.models import EvidencePack
from evidence.trace_sampler import sample_traces
from evidence.explainer import explain_latency_drift

def build_latency_evidence(
    drift_event_id: str,
    service: str,
    baseline_p95: float,
    current_p95: float
) -> EvidencePack:

    traces_before = sample_traces(service)
    traces_after = sample_traces(service)

    explanation = explain_latency_drift(
        service,
        baseline_p95,
        current_p95
    )

    return EvidencePack(
        drift_event_id=drift_event_id,
        baseline_metrics={"p95_ms": baseline_p95},
        current_metrics={"p95_ms": current_p95},
        trace_samples={
            "baseline": traces_before,
            "current": traces_after
        },
        explanation=explanation,
        created_at=datetime.utcnow()
    )
