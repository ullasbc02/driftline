import json
import os
import urllib.error
import urllib.request

from agent.models import SlackNotification


def notify_incident(message: str) -> SlackNotification:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    channel = os.getenv("SLACK_CHANNEL", "#incidents")

    if not webhook_url:
        return SlackNotification(
            status="mocked",
            channel=channel,
            message=message,
            delivered=False,
        )

    body = json.dumps({"text": message}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            delivered = 200 <= response.status < 300
            return SlackNotification(
                status="sent" if delivered else "failed",
                channel=channel,
                message=message,
                delivered=delivered,
                error=None if delivered else f"Slack returned HTTP {response.status}",
            )
    except (urllib.error.URLError, TimeoutError) as exc:
        return SlackNotification(
            status="failed",
            channel=channel,
            message=message,
            delivered=False,
            error=str(exc),
        )
