from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from accountability.models import AuditRecord
from .models import Permission, Role, RolePermission, User, UserRole


SYSTEM_ROLES = {
    "administrator": {
        "name": "Administrator",
        "description": "Full administration within the assigned organization.",
    },
    "content_manager": {
        "name": "Content Manager",
        "description": (
            "Manages organizational content, versions, programs, and assignments."
        ),
    },
    "content_consumer": {
        "name": "Content Consumer",
        "description": (
            "Consumes assigned organizational content according to granted access."
        ),
    },
    "management": {
        "name": "Management",
        "description": (
            "Read-only visibility into authorized organizational resources and reports."
        ),
    },
}


def _codes(*codes):
    return {getattr(Permission.Code, code) for code in codes}


SYSTEM_ROLE_PERMISSIONS = {
    "administrator": _codes(*(code for code, _ in Permission.Code.choices)),
    "content_manager": _codes(
        "PROFILE_VIEW_OWN",
        "PROFILE_UPDATE_OWN",
        "CONTENT_VIEW",
        "CONTENT_SEARCH",
        "CONTENT_CREATE",
        "CONTENT_UPDATE",
        "CONTENT_ARCHIVE",
        "CONTENT_PUBLISH",
        "VERSION_VIEW",
        "VERSION_CREATE",
        "VERSION_PUBLISH",
        "VERSION_ARCHIVE",
        "PROGRAM_VIEW",
        "PROGRAM_CREATE",
        "PROGRAM_UPDATE",
        "ASSIGNMENT_MANAGE",
    ),
    "content_consumer": _codes(
        "PROFILE_VIEW_OWN",
        "PROFILE_UPDATE_OWN",
        "CONTENT_VIEW",
        "CONTENT_SEARCH",
        "VERSION_VIEW",
        "PROGRAM_VIEW",
        "SECURE_DELIVERY",
        "WATERMARK_CONSUME",
        "ACTIVITY_VIEW_OWN",
        "REPORT_VIEW_ASSIGNED",
        "ANALYTICS_VIEW_ASSIGNED",
    ),
    "management": _codes(
        "PROFILE_VIEW_OWN",
        "PROFILE_UPDATE_OWN",
        "CONTENT_VIEW",
        "CONTENT_SEARCH",
        "VERSION_VIEW",
        "PROGRAM_VIEW",
        "ACTIVITY_VIEW_ORGANIZATION",
        "REPORT_VIEW_ORGANIZATION",
        "ANALYTICS_VIEW_ORGANIZATION",
    ),
}


def seed_organization_roles(organization):
    permissions = {}
    for code, name in Permission.Code.choices:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={"name": name},
        )
        permissions[code] = permission

    roles = {}
    for code, defaults in SYSTEM_ROLES.items():
        role, _ = Role.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={**defaults, "is_system_role": True},
        )
        if not role.is_system_role or role.name != defaults["name"]:
            raise ValidationError(
                f"Role code {code!r} conflicts with the system role definition."
            )
        roles[code] = role
        for permission_code in SYSTEM_ROLE_PERMISSIONS[code]:
            RolePermission.objects.get_or_create(
                role=role,
                permission=permissions[permission_code],
            )
    return roles


def _require_role_manager(actor, organization_id):
    if (
        not getattr(actor, "is_authenticated", False)
        or not actor.is_active
        or actor.organization_id != organization_id
        or not has_permission(
            actor,
            Permission.Code.ROLE_MANAGE,
            organization_id=organization_id,
        )
    ):
        raise PermissionDenied("Role management permission is required.")


def _create_role_assignment(user, role, assigned_by):
    if user.organization_id != role.organization_id:
        raise ValidationError("A role can only be assigned within its organization.")
    with transaction.atomic():
        assignment, created = UserRole.objects.get_or_create(
            organization_id=role.organization_id,
            user=user,
            role=role,
            defaults={"assigned_by": assigned_by},
        )
        if created:
            AuditRecord.objects.create(
                organization_id=role.organization_id,
                actor_user=assigned_by,
                action=AuditRecord.Action.USER_ROLE_CHANGED,
                resource_type="user",
                resource_id=user.id,
                new_values={
                    "role_id": str(role.id),
                    "role_code": role.code,
                    "change": "assigned",
                },
                metadata=(
                    {"source": "trusted_command"}
                    if assigned_by is None
                    else None
                ),
            )
        return assignment


def assign_role(user, role, *, assigned_by):
    if user.organization_id != role.organization_id:
        raise ValidationError("A role can only be assigned within its organization.")
    _require_role_manager(assigned_by, role.organization_id)
    return _create_role_assignment(user, role, assigned_by)


def assign_role_from_trusted_command(user, role):
    return _create_role_assignment(user, role, assigned_by=None)


def remove_role(user, role, *, removed_by):
    if user.organization_id != role.organization_id:
        raise ValidationError("A role can only be removed within its organization.")
    _require_role_manager(removed_by, role.organization_id)
    with transaction.atomic():
        assignment = UserRole.objects.select_for_update().filter(
            organization_id=role.organization_id,
            user=user,
            role=role,
        ).first()
        if assignment is None:
            return False
        assignment.delete()
        AuditRecord.objects.create(
            organization_id=role.organization_id,
            actor_user=removed_by,
            action=AuditRecord.Action.USER_ROLE_CHANGED,
            resource_type="user",
            resource_id=user.id,
            old_values={
                "role_id": str(role.id),
                "role_code": role.code,
                "change": "assigned",
            },
            new_values={
                "role_id": str(role.id),
                "role_code": role.code,
                "change": "removed",
            },
        )
        return True


def grant_permission_to_role(role, permission_code, *, granted_by):
    _require_role_manager(granted_by, role.organization_id)
    if (
        role.code == "management"
        and permission_code == Permission.Code.AUDIT_VIEW_ORGANIZATION
    ):
        raise PermissionDenied(
            "Management audit access is unavailable until its record scope is defined."
        )
    permission = Permission.objects.get(code=permission_code)
    with transaction.atomic():
        association, created = RolePermission.objects.get_or_create(
            role=role,
            permission=permission,
        )
        if created:
            AuditRecord.objects.create(
                organization_id=role.organization_id,
                actor_user=granted_by,
                action=AuditRecord.Action.PERMISSION_CHANGED,
                resource_type="role",
                resource_id=role.id,
                new_values={
                    "permission_code": permission.code,
                    "change": "granted",
                },
            )
    return association


def revoke_permission_from_role(role, permission_code, *, revoked_by):
    _require_role_manager(revoked_by, role.organization_id)
    with transaction.atomic():
        association = RolePermission.objects.select_for_update().filter(
            role=role,
            permission__code=permission_code,
        ).first()
        if association is None:
            return False
        permission_code = association.permission.code
        association.delete()
        AuditRecord.objects.create(
            organization_id=role.organization_id,
            actor_user=revoked_by,
            action=AuditRecord.Action.PERMISSION_CHANGED,
            resource_type="role",
            resource_id=role.id,
            old_values={
                "permission_code": permission_code,
                "change": "granted",
            },
            new_values={
                "permission_code": permission_code,
                "change": "revoked",
            },
        )
        return True


def effective_permission_codes(user):
    if not user.is_authenticated or not user.is_active:
        return []
    return sorted(
        set(
            Permission.objects.filter(
                roles__user_roles__organization_id=user.organization_id,
                roles__user_roles__user=user,
                roles__organization_id=user.organization_id,
            ).values_list("code", flat=True)
        )
    )


def effective_role_names(user):
    if not user.is_authenticated or not user.is_active:
        return []
    return sorted(
        set(
            Role.objects.filter(
                user_roles__organization_id=user.organization_id,
                user_roles__user=user,
                organization_id=user.organization_id,
            ).values_list("name", flat=True)
        )
    )


def has_permission(user, permission_code, *, organization_id=None):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if organization_id is not None and organization_id != user.organization_id:
        return False
    return UserRole.objects.filter(
        organization_id=user.organization_id,
        user=user,
        role__organization_id=user.organization_id,
        role__permissions__code=permission_code,
    ).exists()
