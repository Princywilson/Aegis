from rest_framework import serializers

from identity.models import Permission, Role, User
from knowledge.models import (
    Content,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)

from .models import ActivityEvent, AuditRecord, SecurityEvent


def user_display_name(user):
    if user is None:
        return None
    return (
        " ".join(part for part in (user.first_name, user.last_name) if part)
        or None
    )


class ActivityEventSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_version_id = serializers.UUIDField(read_only=True, allow_null=True)
    program_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_access_id = serializers.UUIDField(read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()
    content_title = serializers.CharField(
        source="content.title",
        read_only=True,
        allow_null=True,
    )
    program_name = serializers.CharField(
        source="program.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ActivityEvent
        fields = [
            "id",
            "user_id",
            "user_name",
            "event_type",
            "occurred_at",
            "content_id",
            "content_title",
            "content_version_id",
            "program_id",
            "program_name",
            "content_access_id",
            "metadata",
        ]
        read_only_fields = fields

    def get_user_name(self, event):
        return user_display_name(event.user)


class AuditRecordSerializer(serializers.ModelSerializer):
    actor_user_id = serializers.UUIDField(read_only=True, allow_null=True)
    actor_user_name = serializers.SerializerMethodField()
    resource_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditRecord
        fields = [
            "id",
            "actor_user_id",
            "actor_user_name",
            "action",
            "resource_type",
            "resource_id",
            "resource_name",
            "occurred_at",
            "old_values",
            "new_values",
            "metadata",
        ]
        read_only_fields = fields

    def get_actor_user_name(self, record):
        return user_display_name(record.actor_user)

    def get_resource_name(self, record):
        if record.resource_id is None:
            return None

        cache = getattr(self, "_resource_name_cache", None)
        if cache is None:
            cache = self._resource_name_cache = {}
        key = (record.organization_id, record.resource_type, record.resource_id)
        if key in cache:
            return cache[key]

        organization_id = record.organization_id
        resource_id = record.resource_id
        lookups = {
            "content": lambda: Content.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("title", flat=True).first(),
            "content_version": lambda: ContentVersion.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("content__title", "version_number").first(),
            "program": lambda: Program.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("name", flat=True).first(),
            "content_assignment": lambda: ContentAssignment.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("content__title", "program__name").first(),
            "program_access_grant": lambda: ProgramAccessGrant.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list(
                "user__first_name",
                "user__last_name",
                "program__name",
            ).first(),
            "user": lambda: User.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("first_name", "last_name").first(),
            "role": lambda: Role.objects.filter(
                organization_id=organization_id,
                pk=resource_id,
            ).values_list("name", flat=True).first(),
            "permission": lambda: Permission.objects.filter(
                pk=resource_id,
            ).values_list("name", flat=True).first(),
        }
        result = lookups.get(record.resource_type, lambda: None)()
        if record.resource_type == "content_version" and result:
            name = f"{result[0]} · v{result[1]}"
        elif record.resource_type == "content_assignment" and result:
            name = f"{result[0]} · {result[1]}"
        elif record.resource_type == "program_access_grant" and result:
            user_name = " ".join(part for part in result[:2] if part)
            name = " · ".join(part for part in (user_name, result[2]) if part)
        elif record.resource_type == "user" and result:
            name = " ".join(part for part in result if part) or None
        else:
            name = result
        cache[key] = name
        return name


class SecurityEventSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()
    resource_name = serializers.SerializerMethodField()

    class Meta:
        model = SecurityEvent
        fields = [
            "id",
            "user_id",
            "user_name",
            "event_type",
            "severity",
            "occurred_at",
            "resource_type",
            "resource_id",
            "resource_name",
            "metadata",
        ]
        read_only_fields = fields

    def get_user_name(self, event):
        return user_display_name(event.user)

    def get_resource_name(self, event):
        if event.resource_id is None:
            return None
        if event.resource_type == "content":
            return Content.objects.filter(
                organization_id=event.organization_id,
                pk=event.resource_id,
            ).values_list("title", flat=True).first()
        if event.resource_type == "program":
            return Program.objects.filter(
                organization_id=event.organization_id,
                pk=event.resource_id,
            ).values_list("name", flat=True).first()
        return None
