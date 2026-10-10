from rest_framework import serializers

from .models import ActivityEvent, AuditRecord, SecurityEvent


class ActivityEventSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_version_id = serializers.UUIDField(read_only=True, allow_null=True)
    program_id = serializers.UUIDField(read_only=True, allow_null=True)
    content_access_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = ActivityEvent
        fields = [
            "id",
            "user_id",
            "event_type",
            "occurred_at",
            "content_id",
            "content_version_id",
            "program_id",
            "content_access_id",
            "metadata",
        ]
        read_only_fields = fields


class AuditRecordSerializer(serializers.ModelSerializer):
    actor_user_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = AuditRecord
        fields = [
            "id",
            "actor_user_id",
            "action",
            "resource_type",
            "resource_id",
            "occurred_at",
            "old_values",
            "new_values",
            "metadata",
        ]
        read_only_fields = fields


class SecurityEventSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = SecurityEvent
        fields = [
            "id",
            "user_id",
            "event_type",
            "severity",
            "occurred_at",
            "resource_type",
            "resource_id",
            "metadata",
        ]
        read_only_fields = fields
