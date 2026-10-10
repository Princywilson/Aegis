import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles

from .models import ActivityEvent, AuditRecord, SecurityEvent


class AccountabilityHardeningTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="First",
            slug="first",
        )
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="test-password",
            organization=self.organization,
        )
        roles = seed_organization_roles(self.organization)
        assign_role_from_trusted_command(
            self.user,
            roles["administrator"],
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_accountability_lists_reject_unknown_tenant_or_arbitrary_filters(self):
        for endpoint in (
            "/api/v1/activities/",
            "/api/v1/audits/",
            "/api/v1/security-events/",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    f"{endpoint}?organization_id={uuid.uuid4()}"
                )
                self.assertEqual(response.status_code, 400)

    def test_accountability_lists_require_timezone_aware_dates(self):
        for endpoint in (
            "/api/v1/activities/",
            "/api/v1/audits/",
            "/api/v1/security-events/",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    f"{endpoint}?from=2026-10-10T12:30:00"
                )
                self.assertEqual(response.status_code, 400)

    def test_activity_and_security_events_cannot_be_client_created(self):
        activity_response = self.client.post(
            "/api/v1/activities/",
            {
                "event_type": ActivityEvent.EventType.VIEWER_OPENED,
                "organization_id": str(self.organization.id),
            },
            format="json",
        )
        security_response = self.client.post(
            "/api/v1/security-events/",
            {
                "event_type": "LOGIN_SUCCESS",
                "severity": SecurityEvent.Severity.INFO,
                "organization_id": str(self.organization.id),
            },
            format="json",
        )

        self.assertEqual(activity_response.status_code, 405)
        self.assertEqual(security_response.status_code, 405)
        self.assertEqual(ActivityEvent.objects.count(), 0)
        self.assertEqual(SecurityEvent.objects.count(), 0)

    def test_audit_query_manager_cannot_update_or_delete_historical_rows(self):
        record = AuditRecord.objects.create(
            organization=self.organization,
            actor_user=self.user,
            action=AuditRecord.Action.CONTENT_CREATED,
            resource_type="content",
            resource_id=uuid.uuid4(),
        )

        for operation in (
            lambda: AuditRecord.objects.filter(pk=record.pk).update(
                new_values={"status": "ARCHIVED"}
            ),
            lambda: AuditRecord.objects.filter(pk=record.pk).delete(),
        ):
            with self.assertRaises(ValidationError):
                operation()

        record.refresh_from_db()
        self.assertIsNone(record.new_values)
