from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from accountability.models import SecurityEvent

from .models import ContentAccess


def _latest_qualifying_window(
    records,
    *,
    timestamp_field,
    minimum_events,
    content_field=None,
    minimum_distinct_content=0,
    hours=24,
):
    left = 0
    content_counts = defaultdict(int)
    qualifying_window = None
    window = timedelta(hours=hours)

    for right, record in enumerate(records):
        if content_field:
            content_counts[getattr(record, content_field)] += 1

        while (
            getattr(record, timestamp_field)
            - getattr(records[left], timestamp_field)
            > window
        ):
            if content_field:
                old_content = getattr(records[left], content_field)
                content_counts[old_content] -= 1
                if not content_counts[old_content]:
                    del content_counts[old_content]
            left += 1

        if (
            right - left + 1 >= minimum_events
            and len(content_counts) >= minimum_distinct_content
        ):
            qualifying_window = records[left : right + 1]

    return qualifying_window


def build_risk_signals_for_organization(
    organization_id,
    *,
    start=None,
    end=None,
    hours=24,
):
    end = end or timezone.now()
    start = start or end - timedelta(hours=hours)
    if start > end:
        raise ValueError("The signal start must be earlier than or equal to its end.")

    signals = []
    denied_by_user = defaultdict(list)
    denied_events = SecurityEvent.objects.filter(
        organization_id=organization_id,
        event_type="ACCESS_DENIED",
        resource_type="content",
        user__isnull=False,
        occurred_at__gte=start,
        occurred_at__lte=end,
    ).order_by("user_id", "occurred_at", "id")

    for event in denied_events:
        denied_by_user[event.user_id].append(event)

    for user_id, events in denied_by_user.items():
        window = _latest_qualifying_window(
            events,
            timestamp_field="occurred_at",
            minimum_events=3,
            hours=hours,
        )
        if window:
            signals.append(
                {
                    "type": "REPEATED_DENIALS",
                    "severity": "MEDIUM",
                    "user_id": str(user_id),
                    "event_count": len(window),
                    "first_seen": window[0].occurred_at.isoformat(),
                    "last_seen": window[-1].occurred_at.isoformat(),
                    "reason": "Multiple denied content-access attempts were recorded within 24 hours.",
                }
            )

    granted_by_user = defaultdict(list)
    granted_accesses = ContentAccess.objects.filter(
        organization_id=organization_id,
        access_result=ContentAccess.Result.GRANTED,
        access_context=ContentAccess.Context.CONSUMER,
        accessed_at__gte=start,
        accessed_at__lte=end,
    ).order_by("user_id", "accessed_at", "id")

    for access in granted_accesses:
        granted_by_user[access.user_id].append(access)

    for user_id, accesses in granted_by_user.items():
        window = _latest_qualifying_window(
            accesses,
            timestamp_field="accessed_at",
            minimum_events=4,
            content_field="content_id",
            minimum_distinct_content=3,
            hours=hours,
        )
        if window:
            signals.append(
                {
                    "type": "ACCESS_BURST",
                    "severity": "LOW",
                    "user_id": str(user_id),
                    "event_count": len(window),
                    "content_count": len(
                        {str(access.content_id) for access in window}
                    ),
                    "first_seen": window[0].accessed_at.isoformat(),
                    "last_seen": window[-1].accessed_at.isoformat(),
                    "reason": "The same user accessed multiple distinct content items within 24 hours.",
                }
            )

    return sorted(
        signals,
        key=lambda signal: (
            signal["type"],
            signal.get("last_seen", ""),
            signal.get("user_id", ""),
        ),
    )


def summarize_risk_signals(signals):
    summary = {"total": len(signals), "by_type": {}, "by_severity": {}}
    for signal in signals:
        signal_type = signal["type"]
        severity = signal["severity"]
        summary["by_type"][signal_type] = summary["by_type"].get(signal_type, 0) + 1
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
    return summary
