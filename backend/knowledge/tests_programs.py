from django.test import TestCase
from rest_framework.test import APIClient

from identity.models import Organization, User
from identity.rbac import assign_role_from_trusted_command, seed_organization_roles

from .models import Content, ContentAssignment, Program, ProgramAccessGrant


class ProgramApiTests(TestCase):
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
        other_roles = seed_organization_roles(self.other_organization)
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
            other_roles["content_manager"],
        )
        self.client = APIClient()
        self.programs_url = "/api/v1/programs/"

    def make_program(self, *, organization=None, name="Reference Program"):
        organization = organization or self.organization
        creator = (
            self.other_manager
            if organization == self.other_organization
            else self.manager
        )
        return Program.objects.create(
            organization=organization,
            name=name,
            description="A reusable program.",
            created_by=creator,
        )

    def make_content(self, *, organization=None, title="Reference Content"):
        organization = organization or self.organization
        creator = (
            self.other_manager
            if organization == self.other_organization
            else self.manager
        )
        return Content.objects.create(
            organization=organization,
            title=title,
            created_by=creator,
        )

    def assign_url(self, program):
        return f"{self.programs_url}{program.id}/content/"

    def test_manager_can_create_list_retrieve_and_update_program(self):
        self.client.force_authenticate(self.manager)

        created = self.client.post(
            self.programs_url,
            {"name": "  Reference Program  ", "description": "A program."},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["data"]["name"], "Reference Program")
        self.assertEqual(created.data["data"]["status"], Program.Status.ACTIVE)
        program = Program.objects.get(pk=created.data["data"]["id"])
        self.assertEqual(program.organization, self.organization)
        self.assertEqual(program.created_by, self.manager)

        listing = self.client.get(self.programs_url)
        detail = self.client.get(f"{self.programs_url}{program.id}/")
        updated = self.client.patch(
            f"{self.programs_url}{program.id}/",
            {"name": "Updated Program"},
            format="json",
        )
        self.assertEqual(listing.data["meta"]["total"], 1)
        self.assertEqual(detail.data["data"]["id"], str(program.id))
        self.assertEqual(updated.data["data"]["name"], "Updated Program")

    def test_program_create_rejects_unknown_fields_and_ignores_client_status(self):
        self.client.force_authenticate(self.manager)

        unknown = self.client.post(
            self.programs_url,
            {"name": "Program", "organization": str(self.organization.id)},
            format="json",
        )
        supplied_status = self.client.post(
            self.programs_url,
            {"name": "Program", "status": Program.Status.INACTIVE},
            format="json",
        )

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(supplied_status.status_code, 201)
        self.assertEqual(
            supplied_status.data["data"]["status"],
            Program.Status.ACTIVE,
        )

    def test_consumer_can_view_but_cannot_manage_programs_or_assignments(self):
        program = self.make_program()
        ProgramAccessGrant.objects.create(
            organization=self.organization,
            user=self.consumer,
            program=program,
            granted_by=self.manager,
        )
        content = self.make_content()
        self.client.force_authenticate(self.consumer)

        listing = self.client.get(self.programs_url)
        create = self.client.post(
            self.programs_url,
            {"name": "Unauthorized"},
            format="json",
        )
        assignment = self.client.post(
            self.assign_url(program),
            {"content_id": str(content.id)},
            format="json",
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["meta"]["total"], 1)
        self.assertEqual(create.status_code, 403)
        self.assertEqual(assignment.status_code, 403)

    def test_program_and_content_are_tenant_scoped(self):
        program = self.make_program(organization=self.other_organization)
        content = self.make_content(organization=self.other_organization)
        self.client.force_authenticate(self.manager)

        detail = self.client.get(f"{self.programs_url}{program.id}/")
        listing = self.client.get(self.assign_url(program))
        assignment = self.client.post(
            self.assign_url(self.make_program()),
            {"content_id": str(content.id)},
            format="json",
        )
        content_filter = self.client.get(
            self.programs_url.replace("programs/", "content/"),
            {"program_id": str(program.id)},
        )

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(listing.status_code, 404)
        self.assertEqual(assignment.status_code, 404)
        self.assertEqual(content_filter.status_code, 404)

    def test_content_can_be_assigned_listed_filtered_and_removed(self):
        program = self.make_program()
        content = self.make_content()
        unrelated_content = self.make_content(title="Other Content")
        self.client.force_authenticate(self.manager)

        created = self.client.post(
            self.assign_url(program),
            {"content_id": str(content.id)},
            format="json",
        )
        listing = self.client.get(self.assign_url(program))
        filtered = self.client.get(
            "/api/v1/content/",
            {"program_id": str(program.id)},
        )
        removed = self.client.delete(
            f"{self.assign_url(program)}{content.id}/"
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(
            created.data["data"],
            {
                "program_id": str(program.id),
                "content_id": str(content.id),
            },
        )
        self.assertEqual(listing.data["data"][0]["content_title"], content.title)
        self.assertEqual(filtered.data["meta"]["total"], 1)
        self.assertEqual(filtered.data["data"][0]["id"], str(content.id))
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(ContentAssignment.objects.exists())
        self.assertTrue(Content.objects.filter(pk=content.id).exists())
        self.assertTrue(Content.objects.filter(pk=unrelated_content.id).exists())

    def test_duplicate_assignment_returns_conflict(self):
        program = self.make_program()
        content = self.make_content()
        self.client.force_authenticate(self.manager)
        url = self.assign_url(program)

        first = self.client.post(
            url,
            {"content_id": str(content.id)},
            format="json",
        )
        duplicate = self.client.post(
            url,
            {"content_id": str(content.id)},
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(ContentAssignment.objects.count(), 1)

    def test_inactive_program_preserves_assignments_and_blocks_new_ones(self):
        program = self.make_program()
        existing_content = self.make_content()
        new_content = self.make_content(title="New Content")
        ContentAssignment.objects.create(
            organization=self.organization,
            program=program,
            content=existing_content,
            created_by=self.manager,
        )
        self.client.force_authenticate(self.manager)

        deactivated = self.client.post(
            f"{self.programs_url}{program.id}/deactivate/",
            {},
            format="json",
        )
        blocked = self.client.post(
            self.assign_url(program),
            {"content_id": str(new_content.id)},
            format="json",
        )
        retained = self.client.get(self.assign_url(program))
        reactivated = self.client.post(
            f"{self.programs_url}{program.id}/activate/",
            {},
            format="json",
        )
        allowed = self.client.post(
            self.assign_url(program),
            {"content_id": str(new_content.id)},
            format="json",
        )

        self.assertEqual(deactivated.data["data"]["status"], Program.Status.INACTIVE)
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(len(retained.data["data"]), 1)
        self.assertEqual(reactivated.data["data"]["status"], Program.Status.ACTIVE)
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(ContentAssignment.objects.count(), 2)

    def test_session_mutations_require_csrf(self):
        program = self.make_program()
        content = self.make_content()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.manager)

        denied_create = client.post(
            self.programs_url,
            {"name": "CSRF Protected"},
            format="json",
        )
        csrf_response = client.get("/api/v1/auth/csrf/")
        csrf_token = csrf_response.data["data"]["csrf_token"]
        allowed_create = client.post(
            self.programs_url,
            {"name": "CSRF Protected"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        allowed_assignment = client.post(
            self.assign_url(program),
            {"content_id": str(content.id)},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(denied_create.status_code, 403)
        self.assertEqual(allowed_create.status_code, 201)
        self.assertEqual(allowed_assignment.status_code, 201)
