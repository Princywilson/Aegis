import io
import tempfile
import uuid

import pypdfium2 as pdfium
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from PIL import Image
from rest_framework.test import APIClient

from accountability.models import ActivityEvent, AuditRecord, SecurityEvent
from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles

from .models import ContentAccess, ContentVersion


class ProtectedContentEndToEndTests(TestCase):
    def setUp(self):
        self.private_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.private_root.cleanup)
        self.settings_override = override_settings(
            AEGIS_PRIVATE_STORAGE_ROOT=self.private_root.name,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.organization_a = Organization.objects.create(
            name="Organization A",
            slug="organization-a",
        )
        self.organization_b = Organization.objects.create(
            name="Organization B",
            slug="organization-b",
        )
        self.admin_a = self._create_user(
            "admin@a.example",
            self.organization_a,
        )
        self.consumer_a = self._create_user(
            "consumer@a.example",
            self.organization_a,
        )
        self.admin_b = self._create_user(
            "admin@b.example",
            self.organization_b,
        )
        self.consumer_b = self._create_user(
            "consumer@b.example",
            self.organization_b,
        )

        roles_a = seed_organization_roles(self.organization_a)
        roles_b = seed_organization_roles(self.organization_b)
        for user, role in (
            (self.admin_a, roles_a["administrator"]),
            (self.consumer_a, roles_a["content_consumer"]),
            (self.admin_b, roles_b["administrator"]),
            (self.consumer_b, roles_b["content_consumer"]),
        ):
            assign_role_from_trusted_command(user, role)

        self.client = None
        self.csrf_token = None

    @staticmethod
    def _create_user(email, organization):
        return User.objects.create_user(
            email=email,
            password="test-password",
            organization=organization,
        )

    @staticmethod
    def _pdf_upload():
        document = pdfium.PdfDocument.new()
        document.new_page(160, 100)
        output = io.BytesIO()
        document.save(output)
        document.close()
        return SimpleUploadedFile(
            "reference.pdf",
            output.getvalue(),
            content_type="application/pdf",
        )

    def _authenticate(self, user):
        self.client = APIClient(enforce_csrf_checks=True)
        csrf = self.client.get("/api/v1/auth/csrf/")
        login = self.client.post(
            "/api/v1/auth/login/",
            {
                "organization_slug": user.organization.slug,
                "email": user.email,
                "password": "test-password",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["data"]["csrf_token"],
        )
        self.assertEqual(login.status_code, 200)
        self.csrf_token = self.client.get(
            "/api/v1/auth/csrf/"
        ).data["data"]["csrf_token"]

    def _post(self, path, data, *, format="json"):
        return self.client.post(
            path,
            data,
            format=format,
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

    def test_content_lifecycle_delivery_accountability_and_tenant_isolation(self):
        self._authenticate(self.admin_a)
        content_response = self._post(
            "/api/v1/content/",
            {
                "title": "Controlled reference",
                "description": "End-to-end protected resource",
            },
            format="json",
        )
        self.assertEqual(content_response.status_code, 201)
        content_id = content_response.data["data"]["id"]

        version_response = self._post(
            f"/api/v1/content/{content_id}/versions/",
            {"file": self._pdf_upload(), "version_notes": "Initial version"},
            format="multipart",
        )
        self.assertEqual(version_response.status_code, 201)
        version_id = version_response.data["data"]["id"]

        published = self._post(
            f"/api/v1/content/{content_id}/versions/{version_id}/publish/",
            {},
            format="json",
        )
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data["data"]["status"], ContentVersion.Status.PUBLISHED)

        program_response = self._post(
            "/api/v1/programs/",
            {"name": "Controlled distribution"},
            format="json",
        )
        self.assertEqual(program_response.status_code, 201)
        program_id = program_response.data["data"]["id"]

        assignment = self._post(
            f"/api/v1/programs/{program_id}/content/",
            {"content_id": content_id},
            format="json",
        )
        self.assertEqual(assignment.status_code, 201)

        grant = self._post(
            "/api/v1/program-access-grants/",
            {
                "user_id": str(self.consumer_a.id),
                "program_id": program_id,
            },
            format="json",
        )
        self.assertEqual(grant.status_code, 201)

        self._authenticate(self.consumer_a)
        access_response = self._post(
            f"/api/v1/content/{content_id}/access/",
            {"program_id": program_id},
            format="json",
        )
        self.assertEqual(access_response.status_code, 201)
        access_id = access_response.data["data"]["access_id"]
        delivery = self.client.get(
            f"/api/v1/content/{content_id}/access/{access_id}/delivery/"
        )
        self.assertEqual(delivery.status_code, 200)
        self.assertEqual(delivery["Content-Type"], "image/png")
        with Image.open(io.BytesIO(delivery.content)) as rendered:
            self.assertEqual(rendered.format, "PNG")

        access = ContentAccess.objects.get(pk=access_id)
        self.assertEqual(access.content_version_id, uuid.UUID(version_id))
        self.assertEqual(
            ActivityEvent.objects.filter(
                content_access=access,
                event_type=ActivityEvent.EventType.VIEWER_OPENED,
            ).count(),
            1,
        )
        self.assertEqual(
            ActivityEvent.objects.filter(
                content_access=access,
                event_type=ActivityEvent.EventType.VIEWER_PAGE_RENDERED,
            ).count(),
            1,
        )
        consumer_analytics = self.client.get("/api/v1/analytics/content/")
        consumer_report = self.client.get("/api/v1/reports/access/")
        consumer_audit = self.client.get("/api/v1/audits/")
        self.assertEqual(consumer_analytics.data["data"]["total_views"], 1)
        self.assertEqual(consumer_report.data["meta"]["total"], 1)
        self.assertEqual(consumer_audit.status_code, 403)

        self._authenticate(self.admin_a)
        audit_response = self.client.get("/api/v1/audits/")
        organization_analytics = self.client.get("/api/v1/analytics/content/")
        self.assertEqual(audit_response.status_code, 200)
        self.assertTrue(
            AuditRecord.objects.filter(
                organization=self.organization_a,
                action=AuditRecord.Action.CONTENT_CREATED,
                resource_id=content_id,
            ).exists()
        )
        self.assertEqual(
            organization_analytics.data["data"]["total_views"],
            1,
        )

        self._authenticate(self.admin_b)
        cross_tenant_content = self.client.get(
            f"/api/v1/content/{content_id}/"
        )
        cross_tenant_program = self.client.get(
            f"/api/v1/programs/{program_id}/"
        )
        tenant_a_access_report = self.client.get("/api/v1/reports/access/")
        self.assertEqual(cross_tenant_content.status_code, 404)
        self.assertEqual(cross_tenant_program.status_code, 404)
        self.assertEqual(tenant_a_access_report.data["meta"]["total"], 0)
        self.assertFalse(
            SecurityEvent.objects.filter(
                organization=self.organization_b,
                resource_id=uuid.UUID(content_id),
            ).exists()
        )

        self._authenticate(self.consumer_b)
        cross_tenant_delivery = self._post(
            f"/api/v1/content/{content_id}/access/",
            {"program_id": program_id},
            format="json",
        )
        self.assertEqual(cross_tenant_delivery.status_code, 404)
