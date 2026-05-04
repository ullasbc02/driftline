from typing import Any, Dict, List


def _format_path(edges: List[Dict[str, Any]]) -> str:
    if not edges:
        return "unknown"

    starts = {edge.get("from") for edge in edges}
    ends = {edge.get("to") for edge in edges}
    head = next(iter(starts - ends), edges[0].get("from"))
    path = [head]
    remaining = edges[:]

    while remaining:
        next_index = next(
            (idx for idx, edge in enumerate(remaining) if edge.get("from") == path[-1]),
            None,
        )
        if next_index is None:
            break
        edge = remaining.pop(next_index)
        path.append(edge.get("to"))

    return " -> ".join(part for part in path if part)


def build_report_markdown(
    *,
    drift_event,
    service: str,
    drift_types: List[str],
    severity: int,
    confidence: float,
    root_cause: str,
    evidence_summary: Dict[str, Any],
    decision,
    deployment_context,
) -> str:
    graph_diff = evidence_summary.get("graph_diff", {})
    baseline_path = evidence_summary.get("baseline_path") or "payment-api -> fraud-service"
    current_path = evidence_summary.get("current_path") or _format_path(
        graph_diff.get("current_edges", [])
    )
    latency = evidence_summary.get("latency", {})
    status = evidence_summary.get("status", {})

    latency_line = "No latency regression was measured."
    if latency.get("baseline_p95_ms") is not None and latency.get("current_p95_ms") is not None:
        latency_line = (
            f"p95 latency changed from {latency['baseline_p95_ms']}ms to "
            f"{latency['current_p95_ms']}ms"
        )
        if latency.get("increase_percent") is not None:
            latency_line += f" ({latency['increase_percent']}% increase)."
        else:
            latency_line += "."

    status_line = "No new error class was confirmed."
    if status.get("current_status_counts"):
        status_line = f"Current status distribution: {status['current_status_counts']}."

    return f"""# Incident Report

Service: {service}
Environment: {drift_event.env}
Drift Type: {" + ".join(drift_types)}
Severity: {severity}
Confidence: {confidence:.2f}

## What Changed

The execution graph changed from:

`{baseline_path}`

to:

`{current_path}`

## Likely Root Cause

{root_cause}

Recent deployment context:

- Commit: `{deployment_context.commit_sha}`
- Message: {deployment_context.commit_message}
- Files: {", ".join(deployment_context.changed_files)}

## Impact

{latency_line}
{status_line}

## Evidence

- Added edges: {graph_diff.get("added_edges", [])}
- Removed edges: {graph_diff.get("removed_edges", [])}
- Drift findings: {len(drift_event.findings)}

## Recommended Remediation

{decision.recommendation}

Decision: `{decision.action}`

Rationale: {decision.rationale}
"""
