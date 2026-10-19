from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from identity.models import Permission
from identity.rbac import has_permission

from .models import (
    Content,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)


def user_is_content_consumer_only(user):
    role_codes = set(user.user_roles.values_list("role__code", flat=True))
    return (
        "content_consumer" in role_codes
        and not role_codes.intersection(
            {"administrator", "content_manager", "management"}
        )
    )


def program_queryset_for(user):
    queryset = Program.objects.filter(organization_id=user.organization_id)
    if user_is_content_consumer_only(user):
        now = timezone.now()
        queryset = queryset.filter(
            access_grants__organization_id=user.organization_id,
            access_grants__user=user,
            access_grants__status=ProgramAccessGrant.Status.ACTIVE,
            status=Program.Status.ACTIVE,
        ).filter(
            Q(access_grants__expires_at__isnull=True)
            | Q(access_grants__expires_at__gt=now)
        ).distinct()
    return queryset


def content_queryset_for(user):
    queryset = Content.objects.filter(organization_id=user.organization_id)
    if user_is_content_consumer_only(user):
        queryset = queryset.filter(
            status=Content.Status.PUBLISHED,
            current_version__status=ContentVersion.Status.PUBLISHED,
            program_assignments__organization_id=user.organization_id,
            program_assignments__program__in=program_queryset_for(user),
        ).distinct()
    return queryset


def require_content_search_permissions(user):
    organization_id = user.organization_id
    if not has_permission(
        user,
        Permission.Code.CONTENT_SEARCH,
        organization_id=organization_id,
    ):
        raise PermissionDenied("You are not allowed to search content.")
    if not has_permission(
        user,
        Permission.Code.CONTENT_VIEW,
        organization_id=organization_id,
    ):
        raise PermissionDenied("You are not allowed to view content.")
