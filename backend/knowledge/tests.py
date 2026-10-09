import uuid
import hashlib
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from accountability.models import AuditRecord
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles
from identity.models import Organization, User

from .models import Content, ContentVersion
from .storage import StorageService


class ContentApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="First Organization",
            slug="first",
        )
        self.other_organization = Organization.objects.create(
            name="Second Organization",
            slug="second",
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="test-password",
            organization=self.organization,
        )
        self.other_manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
            organization=self.other_organization,
        )
        self.roles = seed_organization_roles(self.organization)
        self.other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(
            self.manager,
            self.roles["content_manager"],
        )
        assign_role_from_trusted_command(
            self.consumer,
            self.roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.other_manager,
            self.other_roles["content_manager"],
        )
        self.client = APIClient()
        self.list_url = "/api/v1/content/"

    def make_content(
        self,
        *,
        organization=None,
        title="Knowledge resource",
        status=Content.Status.DRAFT,
    ):
        return Content.objects.create(
            organization=organization or self.organization,
            title=title,
            description="A reusable organizational resource.",
            status=status,
            created_by=(
                self.other_manager
                if organization == self.other_organization
                else self.manager
            ),
        )

    def make_version(
        self,
        content,
        version_number,
        *,
        status=ContentVersion.Status.DRAFT,
        organization=None,
        checksum=None,
    ):
        version_id = uuid.uuid4()
        version_organization = organization or content.organization
        return ContentVersion.objects.create(
            id=version_id,
            organization=version_organization,
            content=content,
            version_number=version_number,
            status=status,
            storage_key=StorageService.build_storage_key(
                organization_id=version_organization.id,
                content_id=content.id,
                version_id=version_id,
            ),
            original_filename=f"resource-v{version_number}.pdf",
            mime_type="application/pdf",
            file_size=12,
            checksum=checksum or ("a" * 64),
            created_by=self.manager,
        )

    def upload_url(self, content):
        return f"{self.list_url}{content.id}/versions/"

    @staticmethod
    def pdf_upload(payload=b"%PDF-1.7\ncontent\n", filename="resource.pdf"):
        return SimpleUploadedFile(
            filename,
            payload,
            content_type="application/pdf",
        )

    def test_anonymous_requests_are_unauthenticated(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_FAILED")

    def test_manager_can_create_and_list_organization_content(self):
        self.client.force_authenticate(self.manager)
        created = self.client.post(
            self.list_url,
            {
                "title": "  Knowledge Guide  ",
                "description": "A concise description.",
                "status": Content.Status.PUBLISHED,
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["data"]["title"], "Knowledge Guide")
        self.assertEqual(created.data["data"]["status"], Content.Status.DRAFT)
        content = Content.objects.get(pk=created.data["data"]["id"])
        self.assertEqual(content.organization, self.organization)
        self.assertEqual(content.created_by, self.manager)
        self.assertIsNone(content.current_version_id)

        self.make_content(title="Second resource")
        listing = self.client.get(self.list_url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]), 2)
        self.assertEqual(listing.data["meta"]["total"], 2)

    def test_metadata_can_be_retrieved_and_updated(self):
        content = self.make_content()
        self.client.force_authenticate(self.manager)

        retrieved = self.client.get(f"{self.list_url}{content.id}/")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.data["data"]["title"], content.title)

        updated = self.client.patch(
            f"{self.list_url}{content.id}/",
            {"title": "Revised title", "description": "Revised description."},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        content.refresh_from_db()
        self.assertEqual(content.title, "Revised title")
        self.assertEqual(content.description, "Revised description.")

    def test_session_content_create_update_archive_requires_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.manager)
        csrf_response = client.get("/api/v1/auth/csrf/")
        csrf_token = csrf_response.data["data"]["csrf_token"]

        created = client.post(
            self.list_url,
            {"title": "Session-protected content"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(created.status_code, 201)
        content_id = created.data["data"]["id"]

        updated = client.patch(
            f"{self.list_url}{content_id}/",
            {"title": "Updated session-protected content"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        archived = client.post(
            f"{self.list_url}{content_id}/archive/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.data["data"]["title"],
            "Updated session-protected content",
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.data["data"]["status"], Content.Status.ARCHIVED)

    def test_other_organization_content_is_not_listed_or_retrievable(self):
        own_content = self.make_content()
        other_content = self.make_content(
            organization=self.other_organization,
            title="Private to another tenant",
        )
        self.client.force_authenticate(self.manager)

        listing = self.client.get(self.list_url)
        detail = self.client.get(f"{self.list_url}{other_content.id}/")
        self.assertEqual(listing.data["meta"]["total"], 1)
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(
            listing.data["data"][0]["id"],
            str(own_content.id),
        )

    def test_content_consumer_cannot_list_unassigned_content(self):
        content = self.make_content()
        self.client.force_authenticate(self.consumer)

        listing = self.client.get(self.list_url)
        detail = self.client.get(f"{self.list_url}{content.id}/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"], [])
        self.assertEqual(listing.data["meta"]["total"], 0)
        self.assertEqual(detail.status_code, 404)

    def test_content_consumer_cannot_create_content(self):
        self.client.force_authenticate(self.consumer)

        response = self.client.post(
            self.list_url,
            {"title": "Unauthorized content"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_search_and_filters_validate_inputs(self):
        self.make_content(title="Governance reference")
        self.client.force_authenticate(self.manager)

        search = self.client.get(self.list_url, {"search": "governance"})
        bad_status = self.client.get(self.list_url, {"status": "invalid"})
        bad_page_size = self.client.get(self.list_url, {"page_size": "not-an-int"})
        zero_page_size = self.client.get(self.list_url, {"page_size": "0"})
        unsupported_program_filter = self.client.get(
            self.list_url,
            {"program_id": "00000000-0000-0000-0000-000000000001"},
        )

        self.assertEqual(search.data["meta"]["total"], 1)
        self.assertEqual(bad_status.status_code, 400)
        self.assertEqual(bad_page_size.status_code, 400)
        self.assertEqual(zero_page_size.status_code, 400)
        self.assertEqual(unsupported_program_filter.status_code, 400)

    def test_blank_title_is_rejected(self):
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            self.list_url,
            {"title": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Content.objects.count(), 0)

    def test_unexpected_file_and_tenant_fields_are_rejected(self):
        self.client.force_authenticate(self.manager)

        file_response = self.client.post(
            self.list_url,
            {"title": "Resource", "file": "untrusted-file"},
            format="json",
        )
        tenant_response = self.client.post(
            self.list_url,
            {
                "title": "Resource",
                "organization_id": str(self.other_organization.id),
            },
            format="json",
        )

        self.assertEqual(file_response.status_code, 400)
        self.assertEqual(tenant_response.status_code, 400)
        self.assertEqual(Content.objects.count(), 0)

    def test_content_consumer_is_not_given_organization_scope_by_search(self):
        content = self.make_content()
        self.client.force_authenticate(self.consumer)

        response = self.client.get(self.list_url, {"search": content.title})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])

    def test_archive_updates_content_and_records_actor_and_tenant(self):
        content = self.make_content()
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["status"], Content.Status.ARCHIVED)
        content.refresh_from_db()
        record = AuditRecord.objects.get(resource_id=content.id)
        self.assertEqual(content.status, Content.Status.ARCHIVED)
        self.assertEqual(record.organization_id, self.organization.id)
        self.assertEqual(record.actor_user_id, self.manager.id)
        self.assertEqual(record.action, AuditRecord.Action.CONTENT_ARCHIVED)
        self.assertEqual(record.resource_type, "content")
        self.assertEqual(record.old_values, {"status": Content.Status.DRAFT})
        self.assertEqual(record.new_values, {"status": Content.Status.ARCHIVED})
        self.assertIsNotNone(record.occurred_at)

    def test_archive_is_tenant_scoped_and_requires_archive_permission(self):
        other_content = self.make_content(
            organization=self.other_organization,
            title="Private to another tenant",
        )
        own_content = self.make_content()
        self.client.force_authenticate(self.manager)

        cross_tenant = self.client.post(
            f"{self.list_url}{other_content.id}/archive/",
            {},
            format="json",
        )
        self.assertEqual(cross_tenant.status_code, 404)
        self.assertEqual(
            cross_tenant.data["error"]["code"],
            "RESOURCE_NOT_FOUND",
        )

        self.client.force_authenticate(self.consumer)
        denied = self.client.post(
            f"{self.list_url}{own_content.id}/archive/",
            {},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(AuditRecord.objects.count(), 0)

    def test_rearchive_returns_conflict_without_duplicate_audit(self):
        content = self.make_content(status=Content.Status.ARCHIVED)
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "INVALID_STATE")
        self.assertEqual(AuditRecord.objects.count(), 0)

    def test_audit_insert_failure_rolls_back_content_archive(self):
        content = self.make_content()
        self.client.force_authenticate(self.manager)

        with patch(
            "knowledge.services.AuditRecord.objects.create",
            side_effect=RuntimeError("audit insert failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"{self.list_url}{content.id}/archive/",
                    {},
                    format="json",
                )

        content.refresh_from_db()
        self.assertEqual(content.status, Content.Status.DRAFT)
        self.assertEqual(AuditRecord.objects.count(), 0)

    def test_content_version_number_is_unique_per_content_and_positive(self):
        content = self.make_content()
        self.make_version(content, 1)

        with self.assertRaises(ValidationError):
            self.make_version(content, 1)

        with self.assertRaises(ValidationError):
            self.make_version(content, 0)

    def test_content_version_organization_must_match_content(self):
        content = self.make_content()
        version = ContentVersion(
            organization=self.other_organization,
            content=content,
            version_number=1,
            storage_key="organizations/a/contents/b/versions/c/file",
            original_filename="resource.pdf",
            mime_type="application/pdf",
            file_size=1,
            checksum="a" * 64,
            created_by=self.manager,
        )

        with self.assertRaises(ValidationError):
            version.full_clean()

    def test_published_version_file_identity_is_immutable(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        version.status = ContentVersion.Status.PUBLISHED
        version.save(update_fields=["status"])
        version.checksum = "b" * 64

        with self.assertRaises(ValidationError):
            version.save(update_fields=["checksum"])

    def test_version_list_and_detail_do_not_expose_storage_location(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        self.client.force_authenticate(self.manager)

        listing = self.client.get(f"{self.list_url}{content.id}/versions/")
        detail = self.client.get(
            f"{self.list_url}{content.id}/versions/{version.id}/"
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]), 1)
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("storage_key", detail.data["data"])
        self.assertNotIn("checksum", detail.data["data"])

    def test_content_consumer_cannot_retrieve_unassigned_content_versions(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        self.client.force_authenticate(self.consumer)

        listing = self.client.get(f"{self.list_url}{content.id}/versions/")
        detail = self.client.get(
            f"{self.list_url}{content.id}/versions/{version.id}/"
        )

        self.assertEqual(listing.status_code, 404)
        self.assertEqual(detail.status_code, 404)

    def test_manager_can_upload_pdf_as_private_draft_version(self):
        content = self.make_content()
        payload = b"%PDF-1.7\nprivate file content\n"
        self.client.force_authenticate(self.manager)

        with tempfile.TemporaryDirectory() as storage_root:
            with override_settings(AEGIS_PRIVATE_STORAGE_ROOT=storage_root):
                response = self.client.post(
                    self.upload_url(content),
                    {
                        "file": self.pdf_upload(payload),
                        "version_notes": "Initial file",
                    },
                    format="multipart",
                )

                self.assertEqual(response.status_code, 201)
                version = ContentVersion.objects.get(
                    pk=response.data["data"]["id"]
                )
                self.assertEqual(version.content, content)
                self.assertEqual(version.organization, self.organization)
                self.assertEqual(version.version_number, 1)
                self.assertEqual(version.status, ContentVersion.Status.DRAFT)
                self.assertEqual(version.version_notes, "Initial file")
                self.assertEqual(version.original_filename, "resource.pdf")
                self.assertEqual(version.mime_type, "application/pdf")
                self.assertEqual(version.file_size, len(payload))
                self.assertEqual(version.checksum, hashlib.sha256(payload).hexdigest())
                self.assertNotIn("storage_key", response.data["data"])
                self.assertNotIn("checksum", response.data["data"])
                with StorageService().open_protected_file(version.storage_key) as file:
                    self.assertEqual(file.read(), payload)

    def test_upload_validates_extension_mime_and_file_signature(self):
        content = self.make_content()
        self.client.force_authenticate(self.manager)

        unsupported = self.client.post(
            self.upload_url(content),
            {"file": self.pdf_upload(filename="resource.ppt")},
            format="multipart",
        )
        spoofed = self.client.post(
            self.upload_url(content),
            {
                "file": SimpleUploadedFile(
                    "resource.pdf",
                    b"not a PDF",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )
        mismatched_mime = self.client.post(
            self.upload_url(content),
            {
                "file": SimpleUploadedFile(
                    "resource.pdf",
                    b"%PDF-1.7\ncontent",
                    content_type="text/plain",
                )
            },
            format="multipart",
        )

        self.assertEqual(unsupported.status_code, 400)
        self.assertEqual(spoofed.status_code, 400)
        self.assertEqual(mismatched_mime.status_code, 400)
        self.assertEqual(content.versions.count(), 0)

    def test_upload_rejects_unknown_fields_and_cross_tenant_content(self):
        content = self.make_content()
        other_content = self.make_content(organization=self.other_organization)
        self.client.force_authenticate(self.manager)

        unexpected = self.client.post(
            self.upload_url(content),
            {
                "file": self.pdf_upload(),
                "organization_id": str(self.other_organization.id),
            },
            format="multipart",
        )
        cross_tenant = self.client.post(
            self.upload_url(other_content),
            {"file": self.pdf_upload()},
            format="multipart",
        )

        self.assertEqual(unexpected.status_code, 400)
        self.assertEqual(cross_tenant.status_code, 404)
        self.assertEqual(content.versions.count(), 0)
        self.assertEqual(other_content.versions.count(), 0)

    def test_upload_requires_version_create_permission(self):
        content = self.make_content()
        self.client.force_authenticate(self.consumer)

        response = self.client.post(
            self.upload_url(content),
            {"file": self.pdf_upload()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(content.versions.count(), 0)

    def test_session_upload_requires_csrf_and_accepts_token(self):
        content = self.make_content()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.manager)
        csrf_response = client.get("/api/v1/auth/csrf/")
        csrf_token = csrf_response.data["data"]["csrf_token"]

        with tempfile.TemporaryDirectory() as storage_root:
            with override_settings(AEGIS_PRIVATE_STORAGE_ROOT=storage_root):
                missing_token = client.post(
                    self.upload_url(content),
                    {"file": self.pdf_upload()},
                    format="multipart",
                )
                accepted = client.post(
                    self.upload_url(content),
                    {"file": self.pdf_upload()},
                    format="multipart",
                    HTTP_X_CSRFTOKEN=csrf_token,
                )

        self.assertEqual(missing_token.status_code, 403)
        self.assertEqual(missing_token.data["error"]["code"], "FORBIDDEN")
        self.assertEqual(accepted.status_code, 201)

    def test_failed_version_insert_removes_private_file(self):
        content = self.make_content()
        self.client.force_authenticate(self.manager)

        with tempfile.TemporaryDirectory() as storage_root:
            with override_settings(AEGIS_PRIVATE_STORAGE_ROOT=storage_root):
                with patch(
                    "knowledge.services.ContentVersion.save",
                    side_effect=DatabaseError("insert failed"),
                ):
                    with self.assertRaises(DatabaseError):
                        self.client.post(
                            self.upload_url(content),
                            {"file": self.pdf_upload()},
                            format="multipart",
                        )
                self.assertEqual(content.versions.count(), 0)
                remaining_files = [
                    path
                    for path in Path(storage_root).rglob("*")
                    if path.is_file()
                ]
                self.assertEqual(remaining_files, [])

    def test_publish_sets_current_version_and_writes_audit_record(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/versions/{version.id}/publish/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["status"],
            ContentVersion.Status.PUBLISHED,
        )
        content.refresh_from_db()
        version.refresh_from_db()
        audit_record = AuditRecord.objects.get(
            action=AuditRecord.Action.CONTENT_VERSION_PUBLISHED,
            resource_id=version.id,
        )
        self.assertEqual(content.status, Content.Status.PUBLISHED)
        self.assertEqual(content.current_version_id, version.id)
        self.assertEqual(version.status, ContentVersion.Status.PUBLISHED)
        self.assertIsNotNone(version.published_at)
        self.assertEqual(audit_record.organization_id, self.organization.id)
        self.assertEqual(audit_record.actor_user_id, self.manager.id)

    def test_publishing_new_version_archives_previous_current_version(self):
        content = self.make_content()
        old_version = self.make_version(
            content,
            1,
            status=ContentVersion.Status.PUBLISHED,
        )
        content.status = Content.Status.PUBLISHED
        content.current_version = old_version
        content.save(update_fields=["status", "current_version"])
        new_version = self.make_version(content, 2)
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/versions/{new_version.id}/publish/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        old_version.refresh_from_db()
        new_version.refresh_from_db()
        content.refresh_from_db()
        self.assertEqual(old_version.status, ContentVersion.Status.ARCHIVED)
        self.assertIsNotNone(old_version.archived_at)
        self.assertEqual(new_version.status, ContentVersion.Status.PUBLISHED)
        self.assertEqual(content.current_version_id, new_version.id)

    def test_archive_non_current_draft_version_preserves_audit_history(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/versions/{version.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        version.refresh_from_db()
        audit_record = AuditRecord.objects.get(
            action=AuditRecord.Action.CONTENT_VERSION_ARCHIVED,
            resource_id=version.id,
        )
        self.assertEqual(version.status, ContentVersion.Status.ARCHIVED)
        self.assertIsNotNone(version.archived_at)
        self.assertEqual(audit_record.actor_user_id, self.manager.id)
        self.assertEqual(audit_record.old_values, {"status": ContentVersion.Status.DRAFT})
        self.assertEqual(
            audit_record.new_values,
            {"status": ContentVersion.Status.ARCHIVED},
        )

    def test_archive_non_current_published_version(self):
        content = self.make_content(status=Content.Status.PUBLISHED)
        current_version = self.make_version(
            content,
            2,
            status=ContentVersion.Status.PUBLISHED,
        )
        historical_version = self.make_version(
            content,
            1,
            status=ContentVersion.Status.PUBLISHED,
        )
        content.current_version = current_version
        content.save(update_fields=["current_version"])
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/versions/{historical_version.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        historical_version.refresh_from_db()
        content.refresh_from_db()
        self.assertEqual(
            historical_version.status,
            ContentVersion.Status.ARCHIVED,
        )
        self.assertEqual(content.current_version_id, current_version.id)

    def test_current_version_cannot_be_archived(self):
        content = self.make_content(status=Content.Status.PUBLISHED)
        version = self.make_version(
            content,
            1,
            status=ContentVersion.Status.PUBLISHED,
        )
        content.current_version = version
        content.save(update_fields=["current_version"])
        self.client.force_authenticate(self.manager)

        response = self.client.post(
            f"{self.list_url}{content.id}/versions/{version.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "INVALID_STATE")
        version.refresh_from_db()
        content.refresh_from_db()
        self.assertEqual(version.status, ContentVersion.Status.PUBLISHED)
        self.assertEqual(content.current_version_id, version.id)
        self.assertFalse(
            AuditRecord.objects.filter(
                action=AuditRecord.Action.CONTENT_VERSION_ARCHIVED
            ).exists()
        )

    def test_archive_requires_permission_and_is_tenant_scoped(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        other_content = self.make_content(organization=self.other_organization)
        other_version = self.make_version(other_content, 1)

        self.client.force_authenticate(self.consumer)
        denied = self.client.post(
            f"{self.list_url}{content.id}/versions/{version.id}/archive/",
            {},
            format="json",
        )
        self.client.force_authenticate(self.manager)
        cross_tenant = self.client.post(
            f"{self.list_url}{other_content.id}/versions/{other_version.id}/archive/",
            {},
            format="json",
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(cross_tenant.status_code, 404)
        self.assertEqual(AuditRecord.objects.count(), 0)

    def test_rearchive_and_audit_failure_are_conflicts_or_roll_back(self):
        content = self.make_content()
        archived_version = self.make_version(
            content,
            1,
            status=ContentVersion.Status.ARCHIVED,
        )
        rollback_version = self.make_version(content, 2)
        self.client.force_authenticate(self.manager)

        repeated = self.client.post(
            f"{self.list_url}{content.id}/versions/{archived_version.id}/archive/",
            {},
            format="json",
        )
        self.assertEqual(repeated.status_code, 409)

        with patch(
            "knowledge.services.AuditRecord.objects.create",
            side_effect=RuntimeError("audit insert failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"{self.list_url}{content.id}/versions/{rollback_version.id}/archive/",
                    {},
                    format="json",
                )

        rollback_version.refresh_from_db()
        self.assertEqual(rollback_version.status, ContentVersion.Status.DRAFT)
        self.assertIsNone(rollback_version.archived_at)

    def test_publish_rejects_non_draft_and_cross_tenant_versions(self):
        content = self.make_content()
        published_version = self.make_version(
            content,
            1,
            status=ContentVersion.Status.PUBLISHED,
        )
        other_content = self.make_content(
            organization=self.other_organization,
            title="Other tenant content",
        )
        other_version = self.make_version(other_content, 1)
        self.client.force_authenticate(self.manager)

        already_published = self.client.post(
            f"{self.list_url}{content.id}/versions/{published_version.id}/publish/",
            {},
            format="json",
        )
        other_tenant = self.client.post(
            f"{self.list_url}{content.id}/versions/{other_version.id}/publish/",
            {},
            format="json",
        )

        self.assertEqual(already_published.status_code, 409)
        self.assertEqual(other_tenant.status_code, 404)
        self.assertEqual(
            AuditRecord.objects.filter(
                action=AuditRecord.Action.CONTENT_VERSION_PUBLISHED,
            ).count(),
            0,
        )

    def test_publish_requires_permission_and_rolls_back_if_audit_fails(self):
        content = self.make_content()
        version = self.make_version(content, 1)
        self.client.force_authenticate(self.consumer)

        denied = self.client.post(
            f"{self.list_url}{content.id}/versions/{version.id}/publish/",
            {},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.manager)
        with patch(
            "knowledge.services.AuditRecord.objects.create",
            side_effect=RuntimeError("audit insert failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"{self.list_url}{content.id}/versions/{version.id}/publish/",
                    {},
                    format="json",
                )

        content.refresh_from_db()
        version.refresh_from_db()
        self.assertEqual(content.status, Content.Status.DRAFT)
        self.assertIsNone(content.current_version_id)
        self.assertEqual(version.status, ContentVersion.Status.DRAFT)
        self.assertIsNone(version.published_at)
        self.assertEqual(AuditRecord.objects.count(), 0)
