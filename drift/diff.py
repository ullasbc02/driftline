from typing import Dict, Any, List, Tuple, Optional
from drift.models import DriftFinding

def _edge_id(e: Dict[str, Any]) -> Tuple[str, str]:
    return (e.get("from", "unknown"), e.get("to", "unknown"))

def _profile_id(p: Dict[str, Any]) -> Tuple[str, str, str, str]:
    # (service, method, route, env) but env is already per baseline/current payload
    return (
        p.get("service", "unknown"),
        p.get("http_method", "unknown"),
        p.get("http_route", "unknown"),
        p.get("env", "unknown"),
    )

def _rate(status_counts: Dict[str, int], total: int, key: str) -> float:
    if total <= 0:
        return 0.0
    return float(status_counts.get(key, 0)) / float(total)

def _severity_from_ratio(ratio: float) -> int:
    # very simple scoring for MVP
    if ratio >= 3.0: return 90
    if ratio >= 2.0: return 75
    if ratio >= 1.5: return 60
    if ratio >= 1.25: return 45
    return 20

def diff_baseline_vs_current(baseline: Dict[str, Any], current: Dict[str, Any]) -> List[DriftFinding]:
    findings: List[DriftFinding] = []

    # ---------- PATH DRIFT (graph edges) ----------
    b_edges = baseline.get("graph", {}).get("edges", []) or []
    c_edges = current.get("graph", {}).get("edges", []) or []

    b_edge_set = {_edge_id(e) for e in b_edges}
    c_edge_set = {_edge_id(e) for e in c_edges}

    added = sorted(list(c_edge_set - b_edge_set))
    removed = sorted(list(b_edge_set - c_edge_set))

    for frm, to in added:
        findings.append(DriftFinding(
            drift_type="path_drift",
            subject=f"edge {frm} -> {to}",
            severity=70,
            baseline={"present": False},
            current={"present": True},
            explanation=f"New dependency edge appeared: {frm} → {to}"
        ))

    for frm, to in removed:
        findings.append(DriftFinding(
            drift_type="path_drift",
            subject=f"edge {frm} -> {to}",
            severity=70,
            baseline={"present": True},
            current={"present": False},
            explanation=f"Dependency edge disappeared: {frm} → {to}"
        ))

    # ---------- EDGE LATENCY DRIFT ----------
    # Compare p95 on edges that exist in both snapshots
    b_edge_map = { _edge_id(e): e for e in b_edges }
    c_edge_map = { _edge_id(e): e for e in c_edges }

    for eid in (b_edge_set & c_edge_set):
        b = b_edge_map.get(eid, {})
        c = c_edge_map.get(eid, {})
        b95 = b.get("p95_ms")
        c95 = c.get("p95_ms")

        if b95 is None or c95 is None or b95 <= 0:
            continue

        ratio = float(c95) / float(b95)
        abs_inc = float(c95) - float(b95)

        if ratio >= 1.5 and abs_inc >= 20:
            frm, to = eid
            findings.append(DriftFinding(
                drift_type="latency_drift",
                subject=f"edge {frm} -> {to}",
                severity=_severity_from_ratio(ratio),
                baseline={"p95_ms": b95},
                current={"p95_ms": c95},
                explanation=f"Edge p95 latency increased {ratio:.2f}× ({b95:.1f}ms → {c95:.1f}ms)"
            ))

    # ---------- ENDPOINT LATENCY + ERROR DRIFT ----------
    b_profiles = baseline.get("profiles", []) or []
    c_profiles = current.get("profiles", []) or []

    b_prof_map = { _profile_id(p): p for p in b_profiles }
    c_prof_map = { _profile_id(p): p for p in c_profiles }

    common = set(b_prof_map.keys()) & set(c_prof_map.keys())

    for pid in common:
        b = b_prof_map[pid]
        c = c_prof_map[pid]

        # latency drift: p95
        b95 = b.get("p95_ms")
        c95 = c.get("p95_ms")
        if b95 is not None and c95 is not None and float(b95) > 0:
            ratio = float(c95) / float(b95)
            abs_inc = float(c95) - float(b95)
            if ratio >= 1.5 and abs_inc >= 20:
                svc, method, route, _ = pid
                findings.append(DriftFinding(
                    drift_type="latency_drift",
                    subject=f"endpoint {svc} {method} {route}",
                    severity=_severity_from_ratio(ratio),
                    baseline={"p95_ms": b95},
                    current={"p95_ms": c95},
                    explanation=f"Endpoint p95 latency increased {ratio:.2f}× ({b95:.1f}ms → {c95:.1f}ms)"
                ))

        # error drift: 5xx rate changes (simple MVP)
        b_total = int(b.get("count", 0) or 0)
        c_total = int(c.get("count", 0) or 0)
        b_sc = b.get("status_counts", {}) or {}
        c_sc = c.get("status_counts", {}) or {}

        b_5xx = _rate(b_sc, b_total, "5xx")
        c_5xx = _rate(c_sc, c_total, "5xx")

        # drift if 5xx appears or increases meaningfully
        if c_total >= 10:  # avoid tiny sample noise
            if b_5xx == 0.0 and c_5xx >= 0.02:
                svc, method, route, _ = pid
                findings.append(DriftFinding(
                    drift_type="error_drift",
                    subject=f"endpoint {svc} {method} {route}",
                    severity=80,
                    baseline={"5xx_rate": b_5xx, "status_counts": b_sc, "count": b_total},
                    current={"5xx_rate": c_5xx, "status_counts": c_sc, "count": c_total},
                    explanation=f"New 5xx errors appeared (0% → {c_5xx*100:.1f}%)"
                ))
            elif (c_5xx - b_5xx) >= 0.03:
                svc, method, route, _ = pid
                findings.append(DriftFinding(
                    drift_type="error_drift",
                    subject=f"endpoint {svc} {method} {route}",
                    severity=70,
                    baseline={"5xx_rate": b_5xx, "status_counts": b_sc, "count": b_total},
                    current={"5xx_rate": c_5xx, "status_counts": c_sc, "count": c_total},
                    explanation=f"5xx rate increased ({b_5xx*100:.1f}% → {c_5xx*100:.1f}%)"
                ))

    return findings
