import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from accountability.models import ActivityEvent
from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles

from .models import (
    Content,
    ContentAccess,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .storage import StorageService


class ContentAnalyticsApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="First",
            slug="first",
        )
        self.other_organization = Organization.objects.create(
            name="Second",
            slug="second",
        )
        self.admin = self._user("admin@example.com", self.organization)
        self.consumer = self._user("consumer@example.com", self.organization)
        self.colleague = self._user("colleague@example.com", self.organization)
        self.manager = self._user("manager@example.com", self.organization)
        self.other_admin = self._user(
            "admin@other.example",
            self.other_organization,
        )

        roles = seed_organization_roles(self.organization)
        other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(self.admin, roles["administrator"])
        assign_role_from_trusted_command(
            self.consumer,
            roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.manager,
            roles["content_manager"],
        )
        assign_role_from_trusted_command(
            self.other_admin,
            other_roles["administrator"],
        )

        self.assigned_program = Program.objects.create(
            organization=self.organization,
            name="Assigned",
            created_by=self.admin,
        )
        self.unassigned_program = Program.objects.create(
            organization=self.organization,
            name="Unassigned",
            created_by=self.admin,
        )
        self.content = self._content(
            self.organization,
            self.admin,
            "Assigned content",
        )
        self.unassigned_content = self._content(
            self.organization,
            self.admin,
            "Unassigned content",
        )
        self.other_content = self._content(
            self.other_organization,
            self.other_admin,
            "Other tenant content",
        )
        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.assigned_program,
            content=self.content,
            created_by=self.admin,
        )
        ContentAssignment.objects.create(
            organization=self.organization,
            program=self.unassigned_program,
            content=self.unassigned_content,
            created_by=self.admin,
        )
        ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=self.assigned_program,
            granted_by=self.admin,
        )
        self.own_access_one = self._access(
            self.consumer,
            self.content,
            self.assigned_program,
        )
        self.own_access_two = self._access(
            self.consumer,
            self.content,
            self.assigned_program,
        )
        self.denied_access = self._access(
            self.consumer,
            self.content,
            self.assigned_program,
            result=ContentAccess.Result.DENIED,
        )
        self.colleague_access = self._access(
            self.colleague,
            self.content,
            self.assigned_program,
        )
        self.unassigned_access = self._access(
            self.consumer,
            self.unassigned_content,
            self.unassigned_program,
        )
        self.other_access = self._access(
            self.other_admin,
            self.other_content,
            None,
        )
        for page_number in range(1, 6):
            ActivityEvent.objects.create(
                organization=self.organization,
                user=self.consumer,
                event_type=ActivityEvent.EventType.VIEWER_PAGE_RENDERED,
                content=self.content,
                content_version=self.content.current_version,
                program=self.assigned_program,
                content_access=self.own_access_one,
                metadata={"page_number": page_number},
            )
        self.client = APIClient()

    @staticmethod
    def _user(email, organization):
        return User.objects.create_user(
            email=email,
            password="test-password",
            organization=organization,
        )

    @staticmethod
    def _content(organization, creator, title):
        content = Content.objects.create(
            organization=organization,
            title=title,
            status=Content.Status.PUBLISHED,
            created_by=creator,
        )
        version_id = uuid.uuid4()
        version = ContentVersion.objects.create(
            id=version_id,
            organization=organization,
            content=content,
            version_number=1,
            status=ContentVersion.Status.PUBLISHED,
            storage_key=StorageService.build_storage_key(
                organization_id=organization.id,
                content_id=content.id,
                version_id=version_id,
            ),
            original_filename="report.pdf",
            mime_type="application/pdf",
            file_size=1,
            checksum="a" * 64,
            created_by=creator,
        )
        content.current_version = version
        content.save(update_fields=["current_version"])
        return content

    @staticmethod
    def _access(
        user,
        content,
        program,
        *,
        result=ContentAccess.Result.GRANTED,
    ):
        return ContentAccess.objects.create(
            organization=content.organization,
            user=user,
            content=content,
            content_version=content.current_version,
            program=program,
            access_result=result,
        )

    def _get(self, user, path):
        self.client.force_authenticate(user)
        return self.client.get(path)

    def test_content_consumer_counts_one_view_per_own_assigned_access(self):
        response = self._get(self.consumer, "/api/v1/analytics/content/")

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["total_views"], 2)
        self.assertEqual(data["active_users"], 1)
        self.assertEqual(
            data["most_viewed_content"],
            {
                "content_id": str(self.content.id),
                "title": "Assigned content",
                "views": 2,
            },
        )
        self.assertEqual(sum(item["views"] for item in data["access_frequency"]), 2)
        self.assertEqual(sum(item["views"] for item in data["version_usage"]), 2)
        self.assertEqual(len(data["recent_activity"]), 5)
        self.assertNotIn("average_session_duration", data)

    def test_organization_analytics_are_tenant_scoped(self):
        response = self._get(self.admin, "/api/v1/analytics/content/")

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["total_views"], 4)
        self.assertEqual(data["active_users"], 2)
        self.assertEqual(
            data["most_viewed_content"]["content_id"],
            str(self.content.id),
        )
        reported_content_ids = {
            item["content_id"] for item in data["version_usage"]
        }
        self.assertIn(str(self.unassigned_content.id), reported_content_ids)
        self.assertNotIn(str(self.other_content.id), reported_content_ids)

    def test_access_report_uses_the_same_assigned_and_tenant_scope(self):
        consumer_response = self._get(
            self.consumer,
            "/api/v1/reports/access/",
        )
        self.assertEqual(consumer_response.status_code, 200)
        self.assertEqual(consumer_response.data["meta"]["total"], 2)
        self.assertEqual(
            {
                item["id"]
                for item in consumer_response.data["data"]
            },
            {
                str(self.own_access_one.id),
                str(self.own_access_two.id),
            },
        )

        organization_response = self._get(
            self.admin,
            "/api/v1/reports/access/",
        )
        self.assertEqual(organization_response.status_code, 200)
        self.assertEqual(organization_response.data["meta"]["total"], 4)

    def test_reports_require_the_matching_permission(self):
        response = self._get(
            self.manager,
            "/api/v1/analytics/content/",
        )

        self.assertEqual(response.status_code, 403)

    def test_assigned_scope_cannot_be_overridden_by_user_or_pagination_filters(self):
        other_user = self._get(
            self.consumer,
            f"/api/v1/analytics/content/?user_id={self.colleague.id}",
        )
        unsupported_pagination = self._get(
            self.consumer,
            "/api/v1/analytics/content/?page=1",
        )

        self.assertEqual(other_user.status_code, 200)
        self.assertEqual(other_user.data["data"]["total_views"], 0)
        self.assertEqual(unsupported_pagination.status_code, 400)

    def test_access_report_filters_and_rejects_invalid_date_ranges(self):
        content_filter = self._get(
            self.admin,
            f"/api/v1/reports/access/?content_id={self.content.id}",
        )
        self.assertEqual(content_filter.status_code, 200)
        self.assertEqual(content_filter.data["meta"]["total"], 3)

        reversed_range = self._get(
            self.admin,
            "/api/v1/reports/access/?from=2026-10-11T00:00:00Z"
            "&to=2026-10-10T00:00:00Z",
        )
        self.assertEqual(reversed_range.status_code, 400)

    def test_analytics_activity_is_not_counted_as_extra_views(self):
        opened_event = ActivityEvent.objects.create(
            organization=self.organization,
            user=self.consumer,
            event_type=ActivityEvent.EventType.VIEWER_OPENED,
            content=self.content,
            content_version=self.content.current_version,
            program=self.assigned_program,
            content_access=self.own_access_one,
        )

        response = self._get(self.consumer, "/api/v1/analytics/content/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total_views"], 2)
        self.assertEqual(
            response.data["data"]["recent_activity"][0]["id"],
            str(opened_event.id),
        )
