import io
import tempfile
import uuid

import pypdfium2 as pdfium
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from PIL import Image, ImageChops
from rest_framework.test import APIClient

from accountability.models import ActivityEvent, AuditRecord, SecurityEvent
from identity.models import Organization, Permission, User
from identity.rbac import (
    assign_role_from_trusted_command,
    revoke_permission_from_role,
    seed_organization_roles,
)

from .models import (
    Content,
    ContentAccess,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .delivery import build_watermark_text, render_content_version
from .storage import StorageService


class ContentDeliveryApiTests(TestCase):
    def setUp(self):
        self.private_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.private_root.cleanup)
        self.settings_override = override_settings(
            AEGIS_PRIVATE_STORAGE_ROOT=self.private_root.name,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.organization = Organization.objects.create(
            name="Delivery Organization",
            slug="delivery-organization",
        )
        self.other_organization = Organization.objects.create(
            name="Other Delivery Organization",
            slug="other-delivery-organization",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Admin-password-for-tests-1!",
            organization=self.organization,
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="Consumer-password-for-tests-1!",
            organization=self.organization,
        )
        self.other_consumer = User.objects.create_user(
            email="consumer@example.com",
            password="Consumer-password-for-tests-2!",
            organization=self.other_organization,
        )
        self.other_admin = User.objects.create_user(
            email="admin@example.com",
            password="correct-horse",
            organization=self.other_organization,
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="Manager-password-for-tests-1!",
            organization=self.organization,
        )
        roles = seed_organization_roles(self.organization)
        other_roles = seed_organization_roles(self.other_organization)
        self.roles = roles
        assign_role_from_trusted_command(self.admin, roles["administrator"])
        assign_role_from_trusted_command(self.manager, roles["content_manager"])
        assign_role_from_trusted_command(
            self.consumer,
            roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.other_consumer,
            other_roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.other_consumer,
            other_roles["content_manager"],
        )
        assign_role_from_trusted_command(
            self.other_admin,
            other_roles["administrator"],
        )
        self.program = Program.objects.create(
            organization=self.organization,
            name="Authorized Program",
            created_by=self.admin,
        )
        self.content = Content.objects.create(
            organization=self.organization,
            title="Protected document",
            status=Content.Status.PUBLISHED,
            created_by=self.admin,
        )
        self.version = self.create_version(self.pdf_bytes(page_count=2))
        self.content.current_version = self.version
        self.content.save(update_fields=["current_version"])
        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.program,
            content=self.content,
            created_by=self.admin,
        )
        ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
            granted_by=self.admin,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.consumer)

    @staticmethod
    def pdf_bytes(*, page_count):
        document = pdfium.PdfDocument.new()
        for _ in range(page_count):
            document.new_page(200, 100)
        output = io.BytesIO()
        document.save(output)
        document.close()
        return output.getvalue()

    @staticmethod
    def image_bytes():
        image = Image.new("RGB", (40, 20), color=(20, 80, 140))
        output = io.BytesIO()
        image.save(output, format="JPEG")
        return output.getvalue()

    def create_version(
        self,
        source,
        *,
        content=None,
        mime_type="application/pdf",
        status=ContentVersion.Status.PUBLISHED,
    ):
        content = content or self.content
        version_id = uuid.uuid4()
        version_number = content.versions.count() + 1
        metadata = StorageService().store(
            organization_id=content.organization_id,
            content_id=content.id,
            version_id=version_id,
            uploaded_file=io.BytesIO(source),
        )
        return ContentVersion.objects.create(
            id=version_id,
            organization=content.organization,
            content=content,
            version_number=version_number,
            status=status,
            storage_key=metadata.storage_key,
            original_filename="protected.pdf",
            mime_type=mime_type,
            file_size=metadata.file_size,
            checksum=metadata.checksum,
            created_by=content.created_by,
        )

    def start_access(self):
        return self.client.post(
            f"/api/v1/content/{self.content.id}/access/",
            {"program_id": str(self.program.id)},
            format="json",
        )

    def delivery_url(self, access_id, *, page=1):
        return (
            f"/api/v1/content/{self.content.id}/access/{access_id}/delivery/"
            f"?page={page}"
        )

    def start_preview(self, content, version):
        return self.client.post(
            f"/api/v1/content/{content.id}/preview/",
            {"version_id": str(version.id)},
            format="json",
        )

    @staticmethod
    def preview_delivery_url(content, access_id, *, page=1):
        return (
            f"/api/v1/content/{content.id}/preview/{access_id}/delivery/"
            f"?page={page}"
        )

    def test_authorized_consumer_receives_only_rendered_pdf_pages(self):
        self.consumer.first_name = "Casey"
        self.consumer.last_name = "Consumer"
        self.consumer.save(update_fields=["first_name", "last_name"])
        started = self.start_access()
        self.assertEqual(started.status_code, 201)
        access = ContentAccess.objects.get(pk=started.data["data"]["access_id"])
        self.assertEqual(access.access_result, ContentAccess.Result.GRANTED)
        self.assertEqual(access.content_version, self.version)
        opened_event = ActivityEvent.objects.get(
            content_access=access,
            event_type=ActivityEvent.EventType.VIEWER_OPENED,
        )
        self.assertEqual(opened_event.user_id, self.consumer.id)

        first_page = self.client.get(self.delivery_url(access.id))
        second_page = self.client.get(self.delivery_url(access.id, page=2))

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page["Content-Type"], "image/png")
        self.assertEqual(first_page["X-Page-Count"], "2")
        self.assertEqual(first_page["Cache-Control"], "private, no-store")
        self.assertEqual(first_page["X-Content-Type-Options"], "nosniff")
        self.assertTrue(first_page.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(
            ActivityEvent.objects.filter(
                content_access=access,
                event_type=ActivityEvent.EventType.VIEWER_PAGE_RENDERED,
            ).count(),
            2,
        )
        watermark = build_watermark_text(access)
        self.assertIn("Casey Consumer", watermark)
        self.assertNotIn("consumer@example.com", watermark)
        self.assertIn("Delivery Organization", watermark)
        self.assertIn("UTC", watermark)
        self.assertIn(f"Content {str(self.content.id).split('-')[0]} v1", watermark)
        original = render_content_version(self.version, page_number=1)
        with Image.open(io.BytesIO(original.content)) as original_image:
            with Image.open(io.BytesIO(first_page.content)) as marked_image:
                self.assertIsNotNone(
                    ImageChops.difference(
                        original_image.convert("RGBA"),
                        marked_image.convert("RGBA"),
                    ).convert("RGB").getbbox()
                )
        with Image.open(io.BytesIO(first_page.content)) as rendered:
            self.assertEqual(rendered.size, (400, 200))

    def test_content_manager_previews_published_and_draft_versions(self):
        self.client.force_authenticate(self.manager)
        draft_content = Content.objects.create(
            organization=self.organization,
            title="Draft document",
            status=Content.Status.DRAFT,
            created_by=self.admin,
        )
        draft_version = self.create_version(
            self.pdf_bytes(page_count=1),
            content=draft_content,
            status=ContentVersion.Status.DRAFT,
        )
        grant_count = ProgramAccessGrant.objects.count()
        assignment_count = ContentAssignment.objects.count()

        for content, version in (
            (self.content, self.version),
            (draft_content, draft_version),
        ):
            with self.subTest(
                content_status=content.status,
                version_status=version.status,
            ):
                started = self.start_preview(content, version)
                self.assertEqual(started.status_code, 201)
                self.assertEqual(
                    started.data["data"]["access_context"],
                    ContentAccess.Context.PREVIEW,
                )
                access = ContentAccess.objects.get(
                    pk=started.data["data"]["access_id"],
                )
                self.assertEqual(access.access_context, ContentAccess.Context.PREVIEW)
                self.assertEqual(access.content_version, version)
                self.assertIsNone(access.program_id)

                opened_event = ActivityEvent.objects.get(
                    content_access=access,
                    event_type=ActivityEvent.EventType.VIEWER_OPENED,
                )
                self.assertEqual(
                    opened_event.metadata["access_context"],
                    ContentAccess.Context.PREVIEW,
                )
                self.assertTrue(
                    AuditRecord.objects.filter(
                        organization=self.organization,
                        actor_user=self.manager,
                        action=AuditRecord.Action.CONTENT_PREVIEW_STARTED,
                        resource_type="content",
                        resource_id=content.id,
                        metadata__preview_session_id=str(access.id),
                    ).exists()
                )

                delivered = self.client.get(
                    self.preview_delivery_url(content, access.id),
                )
                self.assertEqual(delivered.status_code, 200)
                self.assertEqual(delivered["Cache-Control"], "private, no-store")
                self.assertIn("PREVIEW", build_watermark_text(access))
                self.assertTrue(delivered.content.startswith(b"\x89PNG\r\n\x1a\n"))

        self.assertEqual(ProgramAccessGrant.objects.count(), grant_count)
        self.assertEqual(ContentAssignment.objects.count(), assignment_count)

    def test_preview_requires_permission_and_organization_scope(self):
        self.client.force_authenticate(self.consumer)
        no_preview_permission = self.start_preview(self.content, self.version)
        self.assertEqual(no_preview_permission.status_code, 403)

        self.client.force_authenticate(self.other_consumer)
        cross_organization = self.start_preview(self.content, self.version)
        self.assertEqual(cross_organization.status_code, 404)

        self.client.force_authenticate(self.manager)
        foreign_content = Content.objects.create(
            organization=self.other_organization,
            title="Other tenant document",
            status=Content.Status.PUBLISHED,
            created_by=self.other_admin,
        )
        foreign_version = self.create_version(
            self.pdf_bytes(page_count=1),
            content=foreign_content,
        )
        cross_organization_version = self.start_preview(
            self.content,
            foreign_version,
        )
        self.assertEqual(cross_organization_version.status_code, 404)

        malformed = self.client.post(
            f"/api/v1/content/{self.content.id}/preview/",
            {
                "version_id": str(self.version.id),
                "organization_id": str(self.organization.id),
            },
            format="json",
        )
        self.assertEqual(malformed.status_code, 400)
        archived_content = Content.objects.create(
            organization=self.organization,
            title="Archived document",
            status=Content.Status.ARCHIVED,
            created_by=self.admin,
        )
        archived_version = self.create_version(
            self.pdf_bytes(page_count=1),
            content=archived_content,
            status=ContentVersion.Status.ARCHIVED,
        )
        self.assertEqual(
            self.start_preview(archived_content, archived_version).status_code,
            404,
        )
        revoke_permission_from_role(
            self.roles["content_manager"],
            Permission.Code.VERSION_VIEW,
            revoked_by=self.admin,
        )
        no_version_permission = self.start_preview(self.content, self.version)
        self.assertEqual(no_version_permission.status_code, 404)

    def test_preview_page_rechecks_session_owner_permission_and_version_state(self):
        self.client.force_authenticate(self.manager)
        started = self.start_preview(self.content, self.version)
        access_id = started.data["data"]["access_id"]
        preview_url = self.preview_delivery_url(self.content, access_id)

        self.client.force_authenticate(self.admin)
        other_actor = self.client.get(preview_url)
        self.assertEqual(other_actor.status_code, 404)

        self.client.force_authenticate(self.other_consumer)
        other_organization = self.client.get(preview_url)
        self.assertEqual(other_organization.status_code, 404)

        self.client.force_authenticate(self.manager)
        self.content.status = Content.Status.ARCHIVED
        self.content.save(update_fields=["status"])
        archived_content = self.client.get(preview_url)
        self.assertEqual(archived_content.status_code, 404)
        self.content.status = Content.Status.PUBLISHED
        self.content.save(update_fields=["status"])

        self.version.status = ContentVersion.Status.ARCHIVED
        self.version.save(update_fields=["status"])
        archived_version = self.client.get(preview_url)
        self.assertEqual(archived_version.status_code, 404)
        self.version.status = ContentVersion.Status.PUBLISHED
        self.version.save(update_fields=["status"])

        self.manager.status = User.Status.INACTIVE
        self.manager.save(update_fields=["status"])
        inactive_user = self.client.get(preview_url)
        self.assertEqual(inactive_user.status_code, 403)
        self.manager.status = User.Status.ACTIVE
        self.manager.save(update_fields=["status"])

        revoke_permission_from_role(
            self.roles["content_manager"],
            Permission.Code.CONTENT_PREVIEW,
            revoked_by=self.admin,
        )
        revoked_permission = self.client.get(preview_url)
        self.assertEqual(revoked_permission.status_code, 403)

    def test_every_delivery_request_rechecks_user_grant_and_assignment(self):
        started = self.start_access()
        access_id = started.data["data"]["access_id"]
        ProgramAccessGrant.objects.filter(
            user=self.consumer,
            program=self.program,
        ).update(status=ProgramAccessGrant.Status.REVOKED)

        denied = self.client.get(self.delivery_url(access_id))

        self.assertEqual(denied.status_code, 404)
        self.assertTrue(
            SecurityEvent.objects.filter(
                organization=self.organization,
                user=self.consumer,
                event_type="ACCESS_DENIED",
                resource_id=self.content.id,
            ).exists()
        )

    def test_delivery_rechecks_program_and_current_version(self):
        started = self.start_access()
        access_id = started.data["data"]["access_id"]
        self.program.status = Program.Status.INACTIVE
        self.program.save(update_fields=["status"])
        inactive_program = self.client.get(self.delivery_url(access_id))
        self.assertEqual(inactive_program.status_code, 404)

        self.program.status = Program.Status.ACTIVE
        self.program.save(update_fields=["status"])
        started_again = self.start_access()
        previous_access_id = started_again.data["data"]["access_id"]
        next_version = self.create_version(self.pdf_bytes(page_count=1))
        self.content.current_version = next_version
        self.content.save(update_fields=["current_version"])

        stale_version = self.client.get(self.delivery_url(previous_access_id))

        self.assertEqual(stale_version.status_code, 404)

    def test_access_context_cannot_be_used_by_another_user_or_tenant(self):
        started = self.start_access()
        access_id = started.data["data"]["access_id"]
        self.client.force_authenticate(self.other_consumer)

        denied = self.client.get(self.delivery_url(access_id))
        other_tenant = self.client.post(
            f"/api/v1/content/{self.content.id}/access/",
            {"program_id": str(self.program.id)},
            format="json",
        )

        self.assertEqual(denied.status_code, 404)
        self.assertEqual(other_tenant.status_code, 404)

    def test_preview_access_record_cannot_be_bound_to_a_program(self):
        with self.assertRaises(ValidationError):
            ContentAccess.objects.create(
                organization=self.organization,
                user=self.manager,
                content=self.content,
                content_version=self.version,
                program=self.program,
                access_context=ContentAccess.Context.PREVIEW,
            )

    def test_start_access_requires_permission_grant_assignment_and_published_version(self):
        ProgramAccessGrant.objects.filter(
            user=self.consumer,
            program=self.program,
        ).delete()
        self.assertEqual(self.start_access().status_code, 404)

        ContentAssignment.objects.filter(
            program=self.program,
            content=self.content,
        ).delete()
        ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=self.program,
            granted_by=self.admin,
        )
        self.assertEqual(self.start_access().status_code, 404)

        self.content.current_version = None
        self.content.save(update_fields=["current_version"])
        self.assertEqual(self.start_access().status_code, 404)
        self.content.current_version = self.version
        self.content.save(update_fields=["current_version"])

        self.client.force_authenticate(self.manager)
        no_delivery_permission = self.client.post(
            f"/api/v1/content/{self.content.id}/access/",
            {"program_id": str(self.program.id)},
            format="json",
        )
        self.assertEqual(no_delivery_permission.status_code, 403)

        self.client.force_authenticate(self.admin)
        denied = self.client.post(
            f"/api/v1/content/{self.content.id}/access/",
            {"program_id": str(self.program.id)},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)

    def test_invalid_page_and_unsupported_formats_are_rejected(self):
        started = self.start_access()
        access_id = started.data["data"]["access_id"]
        invalid_page = self.client.get(self.delivery_url(access_id, page=3))
        self.assertEqual(invalid_page.status_code, 400)

        image_version = self.create_version(
            self.image_bytes(),
            mime_type="image/jpeg",
        )
        self.content.current_version = image_version
        self.content.save(update_fields=["current_version"])
        image_access = self.start_access()
        image_response = self.client.get(
            self.delivery_url(image_access.data["data"]["access_id"])
        )
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Content-Type"], "image/png")

        pptx_version = self.create_version(
            b"presentation package",
            mime_type=(
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
        )
        self.content.current_version = pptx_version
        self.content.save(update_fields=["current_version"])
        pptx_access = self.start_access()
        unsupported = self.client.get(
            self.delivery_url(pptx_access.data["data"]["access_id"])
        )
        self.assertEqual(unsupported.status_code, 415)

    def test_session_access_start_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.consumer)
        url = f"/api/v1/content/{self.content.id}/access/"
        payload = {"program_id": str(self.program.id)}

        rejected = client.post(url, payload, format="json")
        csrf = client.get("/api/v1/auth/csrf/")
        allowed = client.post(
            url,
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["data"]["csrf_token"],
        )

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(allowed.status_code, 201)

        preview_client = APIClient(enforce_csrf_checks=True)
        preview_client.force_login(self.manager)
        preview_url = f"/api/v1/content/{self.content.id}/preview/"
        preview_payload = {"version_id": str(self.version.id)}
        preview_rejected = preview_client.post(
            preview_url,
            preview_payload,
            format="json",
        )
        preview_csrf = preview_client.get("/api/v1/auth/csrf/")
        preview_allowed = preview_client.post(
            preview_url,
            preview_payload,
            format="json",
            HTTP_X_CSRFTOKEN=preview_csrf.data["data"]["csrf_token"],
        )

        self.assertEqual(preview_rejected.status_code, 403)
        self.assertEqual(preview_allowed.status_code, 201)
