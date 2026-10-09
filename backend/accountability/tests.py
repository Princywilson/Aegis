from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from identity.models import Organization, User

from .models import AuthenticationRateLimitCounter, SecurityEvent
from .services import (
    is_login_rate_limited,
    record_login_failure,
    record_login_success,
)


class SecurityEventModelTests(TestCase):
    def test_platform_event_can_be_recorded_without_organization_or_user(self):
        event = SecurityEvent.objects.create(
            event_type="LOGIN_FAILURE",
            severity=SecurityEvent.Severity.MEDIUM,
            metadata={"organization_resolution": "failed"},
        )

        self.assertIsNone(event.organization_id)
        self.assertIsNone(event.user_id)

    def test_tenant_event_records_its_resolved_organization(self):
        organization = Organization.objects.create(name="Example", slug="example")
        event = SecurityEvent.objects.create(
            organization=organization,
            event_type="LOGIN_FAILURE",
            severity=SecurityEvent.Severity.MEDIUM,
        )

        self.assertEqual(event.organization_id, organization.id)

    def test_security_event_rejects_undefined_severity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SecurityEvent.objects.create(
                    event_type="LOGIN_FAILURE",
                    severity="CRITICAL",
                )


class AuthenticationRateLimitCounterTests(TestCase):
    def test_counter_keys_are_unique_by_type_and_hash(self):
        counter = AuthenticationRateLimitCounter.objects.create(
            key_type=AuthenticationRateLimitCounter.KeyType.ACCOUNT,
            key_hash="a" * 64,
            failure_timestamps=[1.0],
        )

        self.assertEqual(counter.failure_timestamps, [1.0])

    def test_account_is_blocked_after_five_failures_in_rolling_window(self):
        now = timezone.now()
        results = [
            record_login_failure(
                "example",
                "person@example.com",
                "192.0.2.1",
                now=now + timedelta(seconds=attempt),
            )
            for attempt in range(5)
        ]

        self.assertEqual(results, [False, False, False, False, True])
        self.assertTrue(
            is_login_rate_limited(
                "example",
                "person@example.com",
                "192.0.2.1",
                now=now + timedelta(seconds=5),
            )
        )
        event = SecurityEvent.objects.filter(event_type="LOGIN_FAILURE").latest(
            "occurred_at"
        )
        self.assertEqual(event.severity, SecurityEvent.Severity.MEDIUM)
        self.assertTrue(event.metadata["rate_limit_triggered"])

    def test_source_ip_is_blocked_after_twenty_failures(self):
        now = timezone.now()
        results = [
            record_login_failure(
                f"organization-{attempt}",
                f"person-{attempt}@example.com",
                "192.0.2.20",
                now=now + timedelta(seconds=attempt),
            )
            for attempt in range(20)
        ]

        self.assertEqual(sum(results), 1)
        self.assertTrue(
            is_login_rate_limited(
                "different-organization",
                "another@example.com",
                "192.0.2.20",
                now=now + timedelta(seconds=21),
            )
        )

    def test_counter_expires_outside_rolling_window(self):
        now = timezone.now()
        record_login_failure(
            "example",
            "person@example.com",
            "192.0.2.1",
            now=now,
        )

        self.assertFalse(
            is_login_rate_limited(
                "example",
                "person@example.com",
                "192.0.2.1",
                now=now + timedelta(minutes=16),
            )
        )
        account_counter = AuthenticationRateLimitCounter.objects.get(
            key_type=AuthenticationRateLimitCounter.KeyType.ACCOUNT
        )
        self.assertEqual(account_counter.failure_timestamps, [])

    def test_success_clears_account_counter_but_not_source_ip_counter(self):
        organization = Organization.objects.create(name="Example", slug="example")
        user = User.objects.create_user(
            email="person@example.com",
            password="correct-password",
            organization=organization,
        )
        record_login_failure("example", user.email, "192.0.2.1")

        self.assertTrue(
            record_login_success(
                organization,
                user,
                "example",
                user.email,
                "192.0.2.1",
            )
        )

        counters = {
            counter.key_type: counter.failure_timestamps
            for counter in AuthenticationRateLimitCounter.objects.all()
        }
        self.assertEqual(counters[AuthenticationRateLimitCounter.KeyType.ACCOUNT], [])
        self.assertEqual(
            len(counters[AuthenticationRateLimitCounter.KeyType.SOURCE_IP]),
            1,
        )
        success_event = SecurityEvent.objects.get(event_type="LOGIN_SUCCESS")
        self.assertEqual(success_event.severity, SecurityEvent.Severity.INFO)

    def test_cleanup_command_removes_expired_rows_but_keeps_active_blocks(self):
        expired = AuthenticationRateLimitCounter.objects.create(
            key_type=AuthenticationRateLimitCounter.KeyType.ACCOUNT,
            key_hash="a" * 64,
        )
        active = AuthenticationRateLimitCounter.objects.create(
            key_type=AuthenticationRateLimitCounter.KeyType.SOURCE_IP,
            key_hash="b" * 64,
            blocked_until=timezone.now() + timedelta(minutes=5),
        )
        AuthenticationRateLimitCounter.objects.filter(pk=expired.pk).update(
            updated_at=timezone.now() - timedelta(minutes=16)
        )
        output = StringIO()

        call_command("cleanup_auth_rate_limits", stdout=output)

        self.assertFalse(
            AuthenticationRateLimitCounter.objects.filter(pk=expired.pk).exists()
        )
        self.assertTrue(
            AuthenticationRateLimitCounter.objects.filter(pk=active.pk).exists()
        )