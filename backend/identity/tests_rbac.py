from io import StringIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from .models import Organization, Permission, Role, User, UserRole
from .permissions import HasAegisPermission
from .rbac import (
    SYSTEM_ROLE_PERMISSIONS,
    assign_role,
    assign_role_from_trusted_command,
    effective_permission_codes,
    effective_role_names,
    grant_permission_to_role,
    has_permission,
    remove_role,
    revoke_permission_from_role,
    seed_organization_roles,
)


class RbacTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="First", slug="first")
        self.other_organization = Organization.objects.create(
            name="Second",
            slug="second",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="correct-password",
            organization=self.organization,
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="correct-password",
            organization=self.organization,
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="correct-password",
            organization=self.other_organization,
        )
        self.roles = seed_organization_roles(self.organization)
        self.other_roles = seed_organization_roles(self.other_organization)
        assign_role_from_trusted_command(self.admin, self.roles["administrator"])
        assign_role(
            self.consumer,
            self.roles["content_consumer"],
            assigned_by=self.admin,
        )
        assign_role_from_trusted_command(
            self.other_user,
            self.other_roles["administrator"],
        )

    def test_seed_command_creates_system_roles_and_catalog_idempotently(self):
        output = StringIO()
        call_command("seed_rbac", stdout=output)
        call_command("seed_rbac", stdout=StringIO())

        for organization in (self.organization, self.other_organization):
            self.assertEqual(
                set(
                    Role.objects.filter(organization=organization).values_list(
                        "code",
                        flat=True,
                    )
                ),
                set(SYSTEM_ROLE_PERMISSIONS),
            )
        self.assertEqual(
            Permission.objects.count(),
            len(Permission.Code.choices),
        )
        self.assertIn("2 organizations", output.getvalue())

    def test_trusted_assignment_command_is_idempotent_and_tenant_scoped(self):
        target = User.objects.create_user(
            email="target@example.com",
            password="correct-password",
            organization=self.organization,
        )
        call_command(
            "assign_user_role",
            "first",
            target.email,
            "content_consumer",
            stdout=StringIO(),
        )
        call_command(
            "assign_user_role",
            "first",
            target.email,
            "content_consumer",
            stdout=StringIO(),
        )

        self.assertEqual(target.user_roles.count(), 1)
        with self.assertRaises(CommandError):
            call_command(
                "assign_user_role",
                "first",
                self.other_user.email,
                "administrator",
                stdout=StringIO(),
            )

    def test_content_consumer_receives_only_approved_role_capabilities(self):
        allowed_codes = {
            Permission.Code.PROFILE_VIEW_OWN,
            Permission.Code.CONTENT_VIEW,
            Permission.Code.VERSION_VIEW,
            Permission.Code.PROGRAM_VIEW,
            Permission.Code.SECURE_DELIVERY,
            Permission.Code.WATERMARK_CONSUME,
            Permission.Code.ACTIVITY_VIEW_OWN,
            Permission.Code.REPORT_VIEW_ASSIGNED,
            Permission.Code.ANALYTICS_VIEW_ASSIGNED,
        }
        self.assertEqual(
            set(effective_permission_codes(self.consumer)),
            allowed_codes
            | {
                Permission.Code.PROFILE_UPDATE_OWN,
                Permission.Code.CONTENT_SEARCH,
            },
        )
        for code in (
            Permission.Code.CONTENT_UPDATE,
            Permission.Code.ASSIGNMENT_MANAGE,
            Permission.Code.ACCESS_GRANT,
            Permission.Code.ACCESS_REVOKE,
            Permission.Code.AUDIT_VIEW_ORGANIZATION,
            Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION,
            Permission.Code.REPORT_VIEW_ORGANIZATION,
            Permission.Code.ANALYTICS_VIEW_ORGANIZATION,
        ):
            self.assertFalse(has_permission(self.consumer, code), code)

    def test_management_is_read_only_and_audit_is_not_enabled_without_scope(self):
        management = User.objects.create_user(
            email="management@example.com",
            password="correct-password",
            organization=self.organization,
        )
        assign_role(
            management,
            self.roles["management"],
            assigned_by=self.admin,
        )

        self.assertTrue(has_permission(management, Permission.Code.CONTENT_VIEW))
        self.assertTrue(
            has_permission(management, Permission.Code.ANALYTICS_VIEW_ORGANIZATION)
        )
        self.assertTrue(
            has_permission(management, Permission.Code.ACTIVITY_VIEW_ORGANIZATION)
        )
        self.assertFalse(
            has_permission(management, Permission.Code.CONTENT_UPDATE)
        )
        self.assertFalse(
            has_permission(management, Permission.Code.AUDIT_VIEW_ORGANIZATION)
        )
        self.assertFalse(
            has_permission(
                management,
                Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION,
            )
        )
        with self.assertRaises(PermissionDenied):
            grant_permission_to_role(
                self.roles["management"],
                Permission.Code.AUDIT_VIEW_ORGANIZATION,
                granted_by=self.admin,
            )

    def test_administrator_is_organization_scoped_without_platform_bypass(self):
        self.assertTrue(
            has_permission(self.admin, Permission.Code.ROLE_MANAGE)
        )
        self.assertTrue(
            has_permission(self.admin, Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION)
        )
        self.assertFalse(
            has_permission(
                self.admin,
                Permission.Code.CONTENT_VIEW,
                organization_id=self.other_organization.id,
            )
        )
        self.assertFalse(
            has_permission(
                self.admin,
                "PLATFORM_ADMIN",
            )
        )
        django_superuser = User.objects.create_superuser(
            email="django-admin@example.com",
            password="correct-password",
            organization=self.organization,
        )
        self.assertFalse(
            has_permission(django_superuser, Permission.Code.CONTENT_VIEW)
        )

    def test_content_manager_requires_explicit_grant_for_access_management(self):
        manager = User.objects.create_user(
            email="manager@example.com",
            password="correct-password",
            organization=self.organization,
        )
        assign_role(
            manager,
            self.roles["content_manager"],
            assigned_by=self.admin,
        )
        self.assertTrue(has_permission(manager, Permission.Code.CONTENT_CREATE))
        self.assertTrue(has_permission(manager, Permission.Code.ASSIGNMENT_MANAGE))
        self.assertFalse(has_permission(manager, Permission.Code.ACCESS_GRANT))
        self.assertFalse(has_permission(manager, Permission.Code.ACCESS_REVOKE))

        with self.assertRaises(PermissionDenied):
            grant_permission_to_role(
                self.roles["content_manager"],
                Permission.Code.ACCESS_GRANT,
                granted_by=self.consumer,
            )
        grant_permission_to_role(
            self.roles["content_manager"],
            Permission.Code.ACCESS_GRANT,
            granted_by=self.admin,
        )
        self.assertTrue(has_permission(manager, Permission.Code.ACCESS_GRANT))
        self.assertTrue(
            revoke_permission_from_role(
                self.roles["content_manager"],
                Permission.Code.ACCESS_GRANT,
                revoked_by=self.admin,
            )
        )
        self.assertFalse(has_permission(manager, Permission.Code.ACCESS_GRANT))

    def test_user_role_assignment_rejects_cross_organization_relationships(self):
        with self.assertRaises(ValidationError):
            assign_role(
                self.consumer,
                self.other_roles["administrator"],
                assigned_by=self.admin,
            )
        with self.assertRaises(ValidationError):
            UserRole.objects.create(
                organization=self.organization,
                user=self.consumer,
                role=self.other_roles["administrator"],
            )
        with self.assertRaises(ValidationError):
            UserRole.objects.create(
                organization=self.organization,
                user=self.consumer,
                role=self.roles["management"],
                assigned_by=self.other_user,
            )
        with self.assertRaises(PermissionDenied):
            assign_role(
                self.consumer,
                self.roles["management"],
                assigned_by=self.other_user,
            )
        self.assertTrue(
            remove_role(
                self.consumer,
                self.roles["content_consumer"],
                removed_by=self.admin,
            )
        )
        self.assertFalse(has_permission(self.consumer, Permission.Code.CONTENT_VIEW))

    def test_inactive_users_have_no_effective_permissions(self):
        self.consumer.status = User.Status.INACTIVE
        self.consumer.save(update_fields=["status"])

        self.assertEqual(effective_role_names(self.consumer), [])
        self.assertEqual(effective_permission_codes(self.consumer), [])
        self.assertFalse(has_permission(self.consumer, Permission.Code.CONTENT_VIEW))

    def test_permission_class_denies_unconfigured_or_ungranted_permissions(self):
        permission = HasAegisPermission()
        request = SimpleNamespace(user=self.consumer)

        self.assertFalse(permission.has_permission(request, SimpleNamespace()))
        self.assertFalse(
            permission.has_permission(
                request,
                SimpleNamespace(required_aegis_permission=Permission.Code.CONTENT_UPDATE),
            )
        )
        self.assertTrue(
            permission.has_permission(
                request,
                SimpleNamespace(required_aegis_permission=Permission.Code.CONTENT_VIEW),
            )
        )

    def test_me_returns_assigned_role_and_effective_permissions(self):
        client = APIClient()
        client.force_login(self.consumer)

        response = client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["roles"], ["Content Consumer"])
        self.assertEqual(
            response.data["data"]["permissions"],
            effective_permission_codes(self.consumer),
        )
        self.assertNotIn(
            Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION,
            response.data["data"]["permissions"],
        )
