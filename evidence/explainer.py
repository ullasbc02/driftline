def explain_latency_drift(
    service: str,
    baseline_p95: float,
    current_p95: float
) -> str:
    delta = current_p95 - baseline_p95
    ratio = current_p95 / baseline_p95

    return (
        f"Latency drift detected for {service}. "
        f"p95 latency increased from {baseline_p95:.1f}ms "
        f"to {current_p95:.1f}ms "
        f"({ratio:.2f}×, +{delta:.1f}ms)."
    )
