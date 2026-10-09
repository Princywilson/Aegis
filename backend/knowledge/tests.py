from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from accountability.models import AuditRecord
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles
from identity.models import Organization, User

from .models import Content


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
