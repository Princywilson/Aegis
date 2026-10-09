import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import AuthenticationRateLimitCounter, SecurityEvent


WINDOW = timedelta(minutes=15)
BLOCK_DURATION = timedelta(minutes=15)
ACCOUNT_FAILURE_LIMIT = 5
SOURCE_IP_FAILURE_LIMIT = 20


def _key_hash(key_type, value):
    message = f"{key_type}:{value}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _counter_keys(organization_slug, email, source_ip):
    user_model = get_user_model()
    normalized_email = user_model.objects.normalize_email(email)
    account_identifier = f"{organization_slug}:{normalized_email}"
    return sorted(
        [
            (
                AuthenticationRateLimitCounter.KeyType.ACCOUNT,
                _key_hash("account", account_identifier),
            ),
            (
                AuthenticationRateLimitCounter.KeyType.SOURCE_IP,
                _key_hash("source-ip", source_ip or "unknown"),
            ),
        ]
    )


def _lock_counters(keys, create_missing=False):
    if create_missing:
        for key_type, key_hash in keys:
            AuthenticationRateLimitCounter.objects.get_or_create(
                key_type=key_type,
                key_hash=key_hash,
            )

    condition = Q(pk__in=[])
    for key_type, key_hash in keys:
        condition |= Q(key_type=key_type, key_hash=key_hash)

    return list(
        AuthenticationRateLimitCounter.objects.select_for_update()
        .filter(condition)
        .order_by("key_type", "key_hash")
    )


def _prune_counter(counter, now):
    cutoff = (now - WINDOW).timestamp()
    timestamps = [
        float(timestamp)
        for timestamp in counter.failure_timestamps
        if float(timestamp) > cutoff
    ]
    blocked_until = counter.blocked_until
    if blocked_until is not None and blocked_until <= now:
        blocked_until = None

    changed = timestamps != counter.failure_timestamps or blocked_until != counter.blocked_until
    if changed:
        counter.failure_timestamps = timestamps
        counter.blocked_until = blocked_until
        counter.updated_at = now
        counter.save(update_fields=["failure_timestamps", "blocked_until", "updated_at"])


def is_login_rate_limited(organization_slug, email, source_ip, now=None):
    now = now or timezone.now()
    keys = _counter_keys(organization_slug, email, source_ip)

    with transaction.atomic():
        counters = _lock_counters(keys)
        for counter in counters:
            _prune_counter(counter, now)
        return any(
            counter.blocked_until is not None and counter.blocked_until > now
            for counter in counters
        )


def record_login_failure(
    organization_slug,
    email,
    source_ip,
    organization=None,
    user=None,
    now=None,
):
    now = now or timezone.now()
    keys = _counter_keys(organization_slug, email, source_ip)

    with transaction.atomic():
        counters = _lock_counters(keys, create_missing=True)
        for counter in counters:
            _prune_counter(counter, now)

        if any(
            counter.blocked_until is not None and counter.blocked_until > now
            for counter in counters
        ):
            return True

        triggered_scopes = []
        for counter in counters:
            counter.failure_timestamps.append(now.timestamp())
            threshold = (
                ACCOUNT_FAILURE_LIMIT
                if counter.key_type == AuthenticationRateLimitCounter.KeyType.ACCOUNT
                else SOURCE_IP_FAILURE_LIMIT
            )
            if len(counter.failure_timestamps) >= threshold:
                counter.blocked_until = now + BLOCK_DURATION
                triggered_scopes.append(counter.key_type)
            counter.updated_at = now
            counter.save(
                update_fields=["failure_timestamps", "blocked_until", "updated_at"]
            )

        SecurityEvent.objects.create(
            organization=organization,
            user=user,
            event_type="LOGIN_FAILURE",
            severity=SecurityEvent.Severity.MEDIUM,
            metadata={"rate_limit_triggered": bool(triggered_scopes), "scopes": triggered_scopes},
        )

        return bool(triggered_scopes)


def record_login_success(organization, user, organization_slug, email, source_ip, now=None):
    now = now or timezone.now()
    keys = _counter_keys(organization_slug, email, source_ip)
    account_key = next(
        key for key in keys if key[0] == AuthenticationRateLimitCounter.KeyType.ACCOUNT
    )

    with transaction.atomic():
        counters = _lock_counters(keys)
        for counter in counters:
            _prune_counter(counter, now)
        if any(
            counter.blocked_until is not None and counter.blocked_until > now
            for counter in counters
        ):
            return False

        account_counter = next(
            (
                counter
                for counter in counters
                if (counter.key_type, counter.key_hash) == account_key
            ),
            None,
        )
        if account_counter is not None:
            account_counter.failure_timestamps = []
            account_counter.blocked_until = None
            account_counter.updated_at = now
            account_counter.save(
                update_fields=["failure_timestamps", "blocked_until", "updated_at"]
            )

        SecurityEvent.objects.create(
            organization=organization,
            user=user,
            event_type="LOGIN_SUCCESS",
            severity=SecurityEvent.Severity.INFO,
        )
        return True


def record_logout(organization, user):
    SecurityEvent.objects.create(
        organization=organization,
        user=user,
        event_type="LOGOUT",
        severity=SecurityEvent.Severity.INFO,
    )
