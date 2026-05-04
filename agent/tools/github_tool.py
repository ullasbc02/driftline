from agent.models import DeploymentContext


def get_deployment_context(drift_event) -> DeploymentContext:
    """
    Mock GitHub/deployment context for the hackathon demo.

    The interface is intentionally shaped like a real integration so it can be
    replaced with GitHub API calls later without changing the incident agent.
    """
    findings_text = " ".join(
        f"{finding.drift_type} {finding.subject} {finding.explanation}"
        for finding in drift_event.findings
    ).lower()

    if "ratelimit-service" in findings_text:
        return DeploymentContext(
            provider="mock-github",
            commit_sha="8f4c2d1",
            commit_message="Added ratelimit-service before fraud-service",
            author="demo@driftline.dev",
            deployed_at="latest deployment",
            changed_files=[
                "demo/payment_api/app.py",
                "docker-compose.yml",
            ],
            summary=(
                "Recent deployment introduced ratelimit-service into the "
                "payment authorization path."
            ),
        )

    if "fraud-service" in findings_text and "latency" in findings_text:
        return DeploymentContext(
            provider="mock-github",
            commit_sha="2b9a7e4",
            commit_message="Enabled expanded fraud checks",
            author="demo@driftline.dev",
            deployed_at="latest deployment",
            changed_files=[
                "demo/fraud_service/app.py",
                "docker-compose.yml",
            ],
            summary="Recent deployment changed fraud-service runtime behavior.",
        )

    return DeploymentContext(
        provider="mock-github",
        commit_sha="b7c8a90",
        commit_message="Updated payment service dependencies",
        author="demo@driftline.dev",
        deployed_at="latest deployment",
        changed_files=["docker-compose.yml"],
        summary="Recent deployment changed the payment service dependency graph.",
    )
