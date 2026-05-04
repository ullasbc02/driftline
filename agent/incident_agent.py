from typing import Any, Dict, List, Optional

from agent.models import IncidentReport
from agent.tools.github_tool import get_deployment_context
from agent.tools.remediation_tool import decide_remediation
from agent.tools.report_tool import build_report_markdown
from agent.tools.slack_tool import notify_incident


def _finding_types(findings) -> List[str]:
    return sorted({finding.drift_type for finding in findings})


def _service_from_subject(subject: str) -> str:
    parts = subject.split()
    if subject.startswith("endpoint ") and len(parts) >= 2:
        return parts[1]
    if subject.startswith("edge ") and len(parts) >= 2:
        return parts[1]
    return "payment-api"


def _edge_from_subject(subject: str) -> Optional[Dict[str, str]]:
    if not subject.startswith("edge ") or " -> " not in subject:
        return None
    raw = subject.replace("edge ", "", 1)
    frm, to = raw.split(" -> ", 1)
    return {"from": frm.strip(), "to": to.strip()}


def _percent_increase(baseline: Optional[float], current: Optional[float]) -> Optional[int]:
    if baseline is None or current is None or baseline <= 0:
        return None
    return round(((current - baseline) / baseline) * 100)


def _status_summary(findings) -> Dict[str, Any]:
    for finding in findings:
        current_counts = finding.current.get("status_counts")
        if current_counts:
            return {
                "baseline_status_counts": finding.baseline.get("status_counts", {}),
                "current_status_counts": current_counts,
            }
    return {}


def _latency_summary(findings, evidence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    baseline_p95 = None
    current_p95 = None

    if evidence:
        baseline_p95 = (evidence.get("baseline_metrics") or {}).get("p95_ms")
        current_p95 = (evidence.get("current_metrics") or {}).get("p95_ms")

    if baseline_p95 is None or current_p95 is None:
        for finding in findings:
            if finding.drift_type != "latency_drift":
                continue
            baseline_p95 = finding.baseline.get("p95_ms")
            current_p95 = finding.current.get("p95_ms")
            break

    return {
        "baseline_p95_ms": baseline_p95,
        "current_p95_ms": current_p95,
        "increase_percent": _percent_increase(baseline_p95, current_p95),
    }


def _graph_summary(findings, evidence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    graph_diff = dict((evidence or {}).get("graph_diff") or {})
    added_edges = list(graph_diff.get("added_edges") or [])
    removed_edges = list(graph_diff.get("removed_edges") or [])

    for finding in findings:
        if finding.drift_type != "path_drift":
            continue
        edge = _edge_from_subject(finding.subject)
        if not edge:
            continue
        if finding.current.get("present") and edge not in added_edges:
            added_edges.append(edge)
        if finding.baseline.get("present") and edge not in removed_edges:
            removed_edges.append(edge)

    graph_diff["added_edges"] = added_edges
    graph_diff["removed_edges"] = removed_edges
    return graph_diff


def _path_from_edges(edges: List[Dict[str, Any]]) -> Optional[str]:
    if not edges:
        return None
    starts = {edge.get("from") for edge in edges}
    ends = {edge.get("to") for edge in edges}
    head = next(iter(starts - ends), edges[0].get("from"))
    path = [head]
    remaining = edges[:]

    while remaining:
        match_index = next(
            (idx for idx, edge in enumerate(remaining) if edge.get("from") == path[-1]),
            None,
        )
        if match_index is None:
            break
        edge = remaining.pop(match_index)
        path.append(edge.get("to"))

    return " -> ".join(part for part in path if part)


def _build_evidence_summary(findings, evidence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    graph_diff = _graph_summary(findings, evidence)
    added_edges = graph_diff.get("added_edges", [])
    removed_edges = graph_diff.get("removed_edges", [])

    baseline_edges = graph_diff.get("baseline_edges") or removed_edges
    current_edges = graph_diff.get("current_edges") or added_edges

    if added_edges and removed_edges:
        current_edges = removed_edges + added_edges
    elif added_edges:
        current_edges = added_edges
    elif removed_edges:
        baseline_edges = removed_edges

    return {
        "latency": _latency_summary(findings, evidence),
        "status": _status_summary(findings),
        "graph_diff": graph_diff,
        "baseline_path": _path_from_edges(baseline_edges),
        "current_path": _path_from_edges(current_edges),
        "evidence_pack_found": bool(evidence),
        "explanation": (evidence or {}).get("explanation"),
    }


def _analyze_root_cause(findings, deployment_context, evidence_summary: Dict[str, Any]) -> tuple[str, float]:
    text = " ".join(
        [deployment_context.commit_message, deployment_context.summary]
        + [finding.subject for finding in findings]
        + [finding.explanation for finding in findings]
    ).lower()

    drift_types = _finding_types(findings)
    has_latency = "latency_drift" in drift_types
    has_path = "path_drift" in drift_types

    if "ratelimit-service" in text:
        confidence = 0.9 if has_path and has_latency else 0.84
        return (
            "Path drift likely caused by a recent dependency change introducing "
            "ratelimit-service between payment-api and fraud-service.",
            confidence,
        )

    if "fraud-service" in text and has_latency:
        return (
            "Latency drift likely caused by the recent fraud-service behavior change.",
            0.82,
        )

    if evidence_summary.get("graph_diff", {}).get("added_edges"):
        return (
            "Path drift likely caused by a recent deployment changing downstream dependencies.",
            0.78,
        )

    return (
        "Driftline found behavioral change, but root cause needs human confirmation.",
        0.62,
    )


def _build_slack_message(
    *,
    drift_event,
    service: str,
    drift_types: List[str],
    severity: int,
    root_cause: str,
    evidence_summary: Dict[str, Any],
    decision,
) -> str:
    latency = evidence_summary.get("latency", {})
    graph_diff = evidence_summary.get("graph_diff", {})
    status = evidence_summary.get("status", {})

    evidence_lines = []
    for edge in graph_diff.get("added_edges", []):
        evidence_lines.append(f"- New edge: {edge.get('from')} -> {edge.get('to')}")
    if latency.get("baseline_p95_ms") is not None and latency.get("current_p95_ms") is not None:
        evidence_lines.append(
            f"- p95 latency increased from {latency['baseline_p95_ms']}ms to {latency['current_p95_ms']}ms"
        )
    if status.get("current_status_counts", {}).get("4xx"):
        evidence_lines.append("- New 4xx responses detected")
    if not evidence_lines:
        evidence_lines.append(f"- {len(drift_event.findings)} drift finding(s) detected")

    drift_label = " + ".join(t.replace("_", " ").title() for t in drift_types)

    return f"""Driftline Incident Commander

Drift detected in {service}.

Type: {drift_label}
Severity: {severity}

Root Cause:
{root_cause}

Evidence:
{chr(10).join(evidence_lines)}

Recommended Action:
{decision.recommendation}
"""


def run_incident_agent(drift_event, evidence: Optional[Dict[str, Any]] = None) -> IncidentReport:
    findings = drift_event.findings
    severity = max((finding.severity for finding in findings), default=0)
    service = _service_from_subject(findings[0].subject) if findings else "payment-api"
    drift_types = _finding_types(findings)

    deployment_context = get_deployment_context(drift_event)
    evidence_summary = _build_evidence_summary(findings, evidence)
    root_cause, confidence = _analyze_root_cause(findings, deployment_context, evidence_summary)
    decision = decide_remediation(severity, confidence, root_cause)
    slack_message = _build_slack_message(
        drift_event=drift_event,
        service=service,
        drift_types=drift_types,
        severity=severity,
        root_cause=root_cause,
        evidence_summary=evidence_summary,
        decision=decision,
    )
    slack = notify_incident(slack_message)
    report_markdown = build_report_markdown(
        drift_event=drift_event,
        service=service,
        drift_types=drift_types,
        severity=severity,
        confidence=confidence,
        root_cause=root_cause,
        evidence_summary=evidence_summary,
        decision=decision,
        deployment_context=deployment_context,
    )

    return IncidentReport(
        drift_event_id=drift_event.id,
        env=drift_event.env,
        service=service,
        drift_types=drift_types,
        severity=severity,
        confidence=confidence,
        root_cause=root_cause,
        deployment_context=deployment_context,
        evidence_summary=evidence_summary,
        decision=decision,
        slack=slack,
        report_markdown=report_markdown,
    )
