from django.test import TestCase
from rest_framework.test import APIClient

from accountability.models import AuditRecord

from .models import Organization, Permission, Role, User
from .rbac import assign_role_from_trusted_command, seed_organization_roles


class OrganizationAdministrationApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="North", slug="north")
        self.other_organization = Organization.objects.create(name="South", slug="south")
        self.roles = seed_organization_roles(self.organization)
        self.other_roles = seed_organization_roles(self.other_organization)
        self.admin = User.objects.create_user(
            email="admin@example.test",
            password="admin-password",
            organization=self.organization,
            first_name="Admin",
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.test",
            password="consumer-password",
            organization=self.organization,
            first_name="Casey",
        )
        self.other_user = User.objects.create_user(
            email="person@example.test",
            password="other-password",
            organization=self.other_organization,
            first_name="Other",
        )
        assign_role_from_trusted_command(self.admin, self.roles["administrator"])
        assign_role_from_trusted_command(
            self.consumer,
            self.roles["content_consumer"],
        )
        assign_role_from_trusted_command(
            self.other_user,
            self.other_roles["administrator"],
        )
        self.client = APIClient()
        self.client.force_login(self.admin)

    def test_user_list_supports_tenant_scoped_filters_and_pagination(self):
        response = self.client.get(
            "/api/v1/users/",
            {
                "search": "casey",
                "role": "content_consumer",
                "status": "active",
                "page_size": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"]["total"], 1)
        self.assertEqual(response.data["meta"]["page_size"], 1)
        self.assertEqual(response.data["data"][0]["id"], str(self.consumer.id))
        self.assertEqual(response.data["data"][0]["roles"], ["Content Consumer"])

    def test_user_list_includes_the_authenticated_administrator(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(self.admin.id),
            {item["id"] for item in response.data["data"]},
        )

    def test_user_creation_assigns_roles_audits_and_returns_password_once(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "name": "Jordan Trainer",
                "email": "jordan@example.test",
                "role_ids": [str(self.roles["content_consumer"].id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        created = User.objects.get(pk=data["id"])
        self.assertEqual(data["name"], "Jordan Trainer")
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["roles"], ["Content Consumer"])
        self.assertTrue(created.check_password(data["temporary_password"]))
        self.assertNotEqual(created.password, data["temporary_password"])
        self.assertEqual(created.organization_id, self.organization.id)
        self.assertEqual(
            AuditRecord.objects.filter(
                organization=self.organization,
                actor_user=self.admin,
                resource_type="user",
                resource_id=created.id,
                action=AuditRecord.Action.USER_CREATED,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditRecord.objects.filter(
                action=AuditRecord.Action.USER_ROLE_CHANGED,
                resource_id=created.id,
            ).count(),
            1,
        )
        self.assertNotIn("temporary_password", User.objects.get(pk=created.id).__dict__)

    def test_user_creation_rejects_cross_tenant_roles_and_duplicate_email(self):
        cross_tenant_role = self.client.post(
            "/api/v1/users/",
            {
                "name": "Cross Tenant",
                "email": "cross@example.test",
                "role_ids": [str(self.other_roles["administrator"].id)],
            },
            format="json",
        )
        duplicate_email = self.client.post(
            "/api/v1/users/",
            {
                "name": "Duplicate",
                "email": self.consumer.email,
            },
            format="json",
        )

        self.assertEqual(cross_tenant_role.status_code, 400)
        self.assertEqual(duplicate_email.status_code, 400)
        self.assertFalse(
            User.objects.filter(
                organization=self.organization,
                email="cross@example.test",
            ).exists()
        )

    def test_user_detail_is_tenant_scoped_and_patch_is_audited(self):
        hidden = self.client.get(f"/api/v1/users/{self.other_user.id}/")
        updated = self.client.patch(
            f"/api/v1/users/{self.consumer.id}/",
            {"name": "Casey Updated", "status": "inactive"},
            format="json",
        )

        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["data"]["name"], "Casey Updated")
        self.assertEqual(updated.data["data"]["status"], "inactive")
        record = AuditRecord.objects.get(
            action=AuditRecord.Action.USER_UPDATED,
            resource_id=self.consumer.id,
        )
        self.assertEqual(record.old_values, {"name": "Casey", "status": "active"})
        self.assertEqual(
            record.new_values,
            {"name": "Casey Updated", "status": "inactive"},
        )

    def test_deactivation_requires_its_dedicated_permission(self):
        permission = Permission.objects.get(code=Permission.Code.USER_UPDATE)
        self.roles["content_consumer"].permissions.add(permission)
        self.client.force_login(self.consumer)

        response = self.client.patch(
            f"/api/v1/users/{self.admin.id}/",
            {"status": "inactive"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.status, User.Status.ACTIVE)

    def test_roles_and_permissions_are_scoped_and_protected(self):
        roles = self.client.get("/api/v1/roles/")
        permissions = self.client.get("/api/v1/permissions/")
        self.assertEqual(roles.status_code, 200)
        self.assertEqual(
            {role["code"] for role in roles.data["data"]},
            set(self.roles),
        )
        self.assertTrue(
            any(
                item["code"] == Permission.Code.USER_CREATE
                for item in permissions.data["data"]
            )
        )

        self.client.force_login(self.consumer)
        self.assertEqual(self.client.get("/api/v1/roles/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/permissions/").status_code, 403)

    def test_list_rejects_unknown_or_invalid_filters(self):
        unknown = self.client.get("/api/v1/users/", {"organization_id": str(self.organization.id)})
        invalid_status = self.client.get("/api/v1/users/", {"status": "pending"})
        invalid_page_size = self.client.get("/api/v1/users/", {"page_size": "0"})

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(invalid_status.status_code, 400)
        self.assertEqual(invalid_page_size.status_code, 400)
