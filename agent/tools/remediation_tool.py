from agent.models import RemediationDecision


def decide_remediation(severity: int, confidence: float, root_cause: str) -> RemediationDecision:
    if severity >= 80 and confidence >= 0.85:
        return RemediationDecision(
            action="recommend_rollback",
            recommendation="Rollback the latest deployment or disable RATE_LIMIT_ENABLED for payment-api.",
            rationale=(
                "Severity and confidence are both high, so Driftline recommends "
                "a rollback path instead of passive monitoring."
            ),
        )

    if severity >= 60:
        return RemediationDecision(
            action="notify_human",
            recommendation="Notify the on-call engineer with the suggested fix before taking action.",
            rationale="Severity is meaningful, but confidence is below the auto-rollback threshold.",
        )

    return RemediationDecision(
        action="monitor_only",
        recommendation="Continue monitoring and wait for more evidence before remediation.",
        rationale="Severity is below the threshold for active remediation.",
    )
