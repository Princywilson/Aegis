import uuid
from datetime import timedelta

from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient

from accountability.models import AuditRecord
from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles

from .models import (
    Content,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .storage import StorageService


class ProgramAccessGrantTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Grant Organization",
            slug="grant-organization",
        )
        self.other_organization = Organization.objects.create(
            name="Other Grant Organization",
            slug="other-grant-organization",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="test-password-only",
            organization=self.organization,
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="test-password-only",
            organization=self.organization,
        )
        self.other_consumer = User.objects.create_user(
            email="consumer@example.com",
            password="test-password-only",
            organization=self.other_organization,
        )
        self.roles = seed_organization_roles(self.organization)
        self.other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(self.admin, self.roles["administrator"])
        assign_role_from_trusted_command(
            self.consumer,
            self.roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.other_consumer,
            self.other_roles["content_consumer"],
        )
        self.client = APIClient()
        self.program = Program.objects.create(
            organization=self.organization,
            name="Authorized Program",
            created_by=self.admin,
        )
        self.content = Content.objects.create(
            organization=self.organization,
            title="Published resource",
            status=Content.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.version = self.make_version(1, ContentVersion.Status.PUBLISHED)
        self.content.current_version = self.version
        self.content.save(update_fields=["current_version"])
        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.program,
            content=self.content,
            created_by=self.admin,
        )

    def make_version(self, number, status):
        version_id = uuid.uuid4()
        return ContentVersion.objects.create(
            id=version_id,
            organization=self.organization,
            content=self.content,
            version_number=number,
            status=status,
            storage_key=StorageService.build_storage_key(
                organization_id=self.organization.id,
                content_id=self.content.id,
                version_id=version_id,
            ),
            original_filename=f"resource-v{number}.pdf",
            mime_type="application/pdf",
            file_size=10,
            checksum=(str(number) * 64),
            created_by=self.admin,
        )

    def create_grant(
        self,
        *,
        user=None,
        program=None,
        expires_at=None,
        actor=None,
    ):
        self.client.force_authenticate(actor or self.admin)
        payload = {
            "user_id": str((user or self.consumer).id),
            "program_id": str((program or self.program).id),
        }
        if expires_at is not None:
            payload["expires_at"] = expires_at.isoformat()
        return self.client.post(
            "/api/v1/program-access-grants/",
            payload,
            format="json",
        )

    def test_grant_revoke_and_regrant_preserve_history(self):
        first = self.create_grant()
        self.assertEqual(first.status_code, 201)
        first_grant = ProgramAccessGrant.objects.get(pk=first.data["data"]["id"])
        self.assertEqual(first_grant.status, ProgramAccessGrant.Status.ACTIVE)
        self.assertEqual(first_grant.granted_by, self.admin)

        duplicate = self.create_grant()
        self.assertEqual(duplicate.status_code, 409)

        self.client.force_authenticate(self.admin)
        revoked = self.client.post(
            f"/api/v1/program-access-grants/{first_grant.id}/revoke/",
            {},
            format="json",
        )
        self.assertEqual(revoked.status_code, 200)
        first_grant.refresh_from_db()
        self.assertEqual(first_grant.status, ProgramAccessGrant.Status.REVOKED)
        self.assertEqual(first_grant.revoked_by, self.admin)
        self.assertIsNotNone(first_grant.revoked_at)

        second = self.create_grant()
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.data["data"]["id"], str(first_grant.id))
        self.assertEqual(
            ProgramAccessGrant.objects.filter(
                user=self.consumer,
                program=self.program,
            ).count(),
            2,
        )
        self.assertEqual(
            AuditRecord.objects.filter(
                action__in=[
                    AuditRecord.Action.PROGRAM_ACCESS_GRANTED,
                    AuditRecord.Action.PROGRAM_ACCESS_REVOKED,
                ]
            ).count(),
            3,
        )

    def test_expired_grants_are_denied_and_regrant_creates_new_history(self):
        expired_time = timezone.now() - timedelta(minutes=1)
        self.client.force_authenticate(self.admin)
        expired_grant = ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
            granted_by=self.admin,
            expires_at=expired_time,
        )

        self.client.force_authenticate(self.consumer)
        content_list = self.client.get("/api/v1/content/")
        version_list = self.client.get(
            f"/api/v1/content/{self.content.id}/versions/"
        )
        own_access = self.client.get(
            f"/api/v1/users/{self.consumer.id}/access/"
        )
        self.assertEqual(content_list.data["data"], [])
        self.assertEqual(version_list.status_code, 404)
        self.assertEqual(
            own_access.data["data"][0]["status"],
            ProgramAccessGrant.Status.EXPIRED,
        )

        second = self.create_grant()
        expired_grant.refresh_from_db()
        self.assertEqual(second.status_code, 201)
        self.assertEqual(expired_grant.status, ProgramAccessGrant.Status.EXPIRED)

    def test_consumer_reads_only_granted_assigned_published_resources(self):
        previous_version = self.make_version(
            2,
            ContentVersion.Status.ARCHIVED,
        )
        self.client.force_authenticate(self.admin)
        grant_response = self.create_grant()
        self.assertEqual(grant_response.status_code, 201)
        self.client.force_authenticate(self.consumer)

        content_list = self.client.get("/api/v1/content/")
        program_list = self.client.get("/api/v1/programs/")
        assignments = self.client.get(
            f"/api/v1/programs/{self.program.id}/content/"
        )
        version_list = self.client.get(
            f"/api/v1/content/{self.content.id}/versions/"
        )
        previous_detail = self.client.get(
            f"/api/v1/content/{self.content.id}/versions/{previous_version.id}/"
        )

        self.assertEqual(
            [item["id"] for item in content_list.data["data"]],
            [str(self.content.id)],
        )
        self.assertEqual(
            [item["id"] for item in program_list.data["data"]],
            [str(self.program.id)],
        )
        self.assertEqual(len(assignments.data["data"]), 1)
        self.assertEqual(
            [item["id"] for item in version_list.data["data"]],
            [str(self.version.id)],
        )
        self.assertEqual(previous_detail.status_code, 404)

    def test_revoke_and_program_deactivation_deny_without_deleting_grant(self):
        grant_response = self.create_grant()
        grant = ProgramAccessGrant.objects.get(pk=grant_response.data["data"]["id"])
        self.client.force_authenticate(self.consumer)

        self.program.status = Program.Status.INACTIVE
        self.program.save(update_fields=["status"])
        inactive_access = self.client.get("/api/v1/content/")
        grant.refresh_from_db()
        self.assertEqual(inactive_access.data["data"], [])
        self.assertEqual(grant.status, ProgramAccessGrant.Status.ACTIVE)

        self.program.status = Program.Status.ACTIVE
        self.program.save(update_fields=["status"])
        restored_access = self.client.get("/api/v1/content/")
        self.assertEqual(len(restored_access.data["data"]), 1)

        self.client.force_authenticate(self.admin)
        revoke = self.client.post(
            f"/api/v1/program-access-grants/{grant.id}/revoke/",
            {},
            format="json",
        )
        self.assertEqual(revoke.status_code, 200)
        self.client.force_authenticate(self.consumer)
        revoked_access = self.client.get("/api/v1/content/")
        self.assertEqual(revoked_access.data["data"], [])
        self.assertTrue(ProgramAccessGrant.objects.filter(pk=grant.id).exists())

    def test_grant_validation_and_tenant_isolation(self):
        invalid_role = self.create_grant(user=self.admin)
        cross_tenant_user = self.create_grant(user=self.other_consumer)
        inactive_program = Program.objects.create(
            organization=self.organization,
            name="Inactive Program",
            status=Program.Status.INACTIVE,
            created_by=self.admin,
        )
        inactive_grant = self.create_grant(program=inactive_program)

        self.assertEqual(invalid_role.status_code, 400)
        self.assertEqual(cross_tenant_user.status_code, 404)
        self.assertEqual(inactive_grant.status_code, 409)
        self.assertEqual(ProgramAccessGrant.objects.count(), 0)

    def test_access_grant_mutations_require_explicit_permission(self):
        from identity.rbac import grant_permission_to_role
        from identity.models import Permission

        manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password-only",
            organization=self.organization,
        )
        manager_role = self.roles["content_manager"]
        assign_role_from_trusted_command(manager, manager_role)

        denied = self.create_grant(actor=manager)
        self.assertEqual(denied.status_code, 403)

        grant_permission_to_role(
            manager_role,
            Permission.Code.ACCESS_GRANT,
            granted_by=self.admin,
        )
        allowed = self.create_grant(actor=manager)
        self.assertEqual(allowed.status_code, 201)
