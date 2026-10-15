import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles
from knowledge.models import Content, Program

from .models import ActivityEvent, AuditRecord, SecurityEvent


class AccountabilityApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="First",
            slug="first",
        )
        self.other_organization = Organization.objects.create(
            name="Second",
            slug="second",
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.colleague = User.objects.create_user(
            email="colleague@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.management = User.objects.create_user(
            email="management@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.other_admin = User.objects.create_user(
            email="admin@other.example",
            password="test-password",
            organization=self.other_organization,
        )
        self.consumer.first_name = "Casey"
        self.consumer.last_name = "Consumer"
        self.consumer.save(update_fields=["first_name", "last_name"])
        self.admin.first_name = "Avery"
        self.admin.last_name = "Admin"
        self.admin.save(update_fields=["first_name", "last_name"])

        roles = seed_organization_roles(self.organization)
        other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(
            self.consumer,
            roles["content_consumer"],
        )
        assign_role_from_trusted_command(self.admin, roles["administrator"])
        assign_role_from_trusted_command(
            self.management,
            roles["management"],
        )
        assign_role_from_trusted_command(
            self.other_admin,
            other_roles["administrator"],
        )

        self.content = Content.objects.create(
            organization=self.organization,
            title="Reference content",
            created_by=self.admin,
        )
        self.program = Program.objects.create(
            organization=self.organization,
            name="Reference program",
            created_by=self.admin,
        )
        self.consumer_activity = self._create_activity(self.consumer)
        self.colleague_activity = self._create_activity(self.colleague)
        self.other_activity = self._create_activity(
            self.other_admin,
            organization=self.other_organization,
        )
        self.tenant_security_event = SecurityEvent.objects.create(
            organization=self.organization,
            user=self.consumer,
            event_type="ACCESS_DENIED",
            severity=SecurityEvent.Severity.MEDIUM,
            resource_type="content",
            resource_id=self.content.id,
        )
        self.platform_security_event = SecurityEvent.objects.create(
            event_type="LOGIN_FAILURE",
            severity=SecurityEvent.Severity.MEDIUM,
        )
        self.other_security_event = SecurityEvent.objects.create(
            organization=self.other_organization,
            user=self.other_admin,
            event_type="ACCESS_DENIED",
            severity=SecurityEvent.Severity.MEDIUM,
        )
        self.audit_record = AuditRecord.objects.create(
            organization=self.organization,
            actor_user=self.admin,
            action=AuditRecord.Action.CONTENT_CREATED,
            resource_type="content",
            resource_id=self.content.id,
            new_values={"title": "Example"},
        )
        self.other_audit_record = AuditRecord.objects.create(
            organization=self.other_organization,
            actor_user=self.other_admin,
            action=AuditRecord.Action.CONTENT_CREATED,
            resource_type="content",
            resource_id=uuid.uuid4(),
        )
        self.client = APIClient()

    def _create_activity(self, user, *, organization=None):
        return ActivityEvent.objects.create(
            organization=organization or user.organization,
            user=user,
            event_type=ActivityEvent.EventType.VIEWER_OPENED,
            content=self.content if user == self.consumer else None,
            program=self.program if user == self.consumer else None,
        )

    def _get(self, user, path):
        self.client.force_authenticate(user)
        return self.client.get(path)

    def test_activity_api_limits_content_consumer_to_own_events(self):
        response = self._get(self.consumer, "/api/v1/activities/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"]["total"], 1)
        self.assertEqual(
            response.data["data"][0]["id"],
            str(self.consumer_activity.id),
        )
        self.assertEqual(response.data["data"][0]["user_name"], "Casey Consumer")
        self.assertEqual(response.data["data"][0]["content_title"], "Reference content")
        self.assertEqual(response.data["data"][0]["program_name"], "Reference program")
        self.assertNotIn(
            str(self.colleague_activity.id),
            {item["id"] for item in response.data["data"]},
        )

    def test_activity_api_allows_management_org_scope_but_not_other_tenants(self):
        response = self._get(self.management, "/api/v1/activities/")

        self.assertEqual(response.status_code, 200)
        event_ids = {item["id"] for item in response.data["data"]}
        self.assertIn(str(self.consumer_activity.id), event_ids)
        self.assertIn(str(self.colleague_activity.id), event_ids)
        self.assertNotIn(str(self.other_activity.id), event_ids)

    def test_activity_api_does_not_allow_consumer_to_filter_for_colleague(self):
        response = self._get(
            self.consumer,
            f"/api/v1/activities/?user_id={self.colleague.id}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"]["total"], 0)

    def test_audit_api_requires_permission_and_is_read_only(self):
        denied = self._get(self.consumer, "/api/v1/audits/")
        self.assertEqual(denied.status_code, 403)

        management_denied = self._get(self.management, "/api/v1/audits/")
        self.assertEqual(management_denied.status_code, 403)

        response = self._get(
            self.admin,
            "/api/v1/audits/?action=CONTENT_CREATED",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"]["total"], 1)
        self.assertEqual(
            response.data["data"][0]["id"],
            str(self.audit_record.id),
        )
        self.assertEqual(response.data["data"][0]["actor_user_name"], "Avery Admin")
        self.assertEqual(response.data["data"][0]["resource_name"], "Reference content")

        self.client.force_authenticate(self.admin)
        update_response = self.client.patch(
            "/api/v1/audits/",
            {"new_values": {"title": "Changed"}},
            format="json",
        )
        self.assertEqual(update_response.status_code, 405)

    def test_security_event_api_excludes_platform_and_other_tenant_rows(self):
        response = self._get(self.admin, "/api/v1/security-events/")

        self.assertEqual(response.status_code, 200)
        event_ids = {item["id"] for item in response.data["data"]}
        self.assertEqual(event_ids, {str(self.tenant_security_event.id)})
        event = response.data["data"][0]
        self.assertEqual(event["user_name"], "Casey Consumer")
        self.assertEqual(event["resource_name"], "Reference content")
        self.assertNotIn(str(self.platform_security_event.id), event_ids)
        self.assertNotIn(str(self.other_security_event.id), event_ids)


class AuditRecordAppendOnlyTests(TestCase):
    def test_existing_audit_record_cannot_be_updated_or_deleted(self):
        organization = Organization.objects.create(
            name="Example",
            slug="example",
        )
        record = AuditRecord.objects.create(
            organization=organization,
            action=AuditRecord.Action.CONTENT_CREATED,
            resource_type="content",
            resource_id=uuid.uuid4(),
        )

        record.new_values = {"title": "Changed"}
        with self.assertRaises(ValidationError):
            record.save()
        with self.assertRaises(ValidationError):
            record.delete()
        with self.assertRaises(ValidationError):
            AuditRecord.objects.filter(pk=record.pk).update(
                new_values={"title": "Changed"}
            )
        with self.assertRaises(ValidationError):
            AuditRecord.objects.filter(pk=record.pk).delete()

        record.refresh_from_db()
        self.assertIsNone(record.new_values)
