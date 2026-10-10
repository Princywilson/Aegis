from django.utils import timezone
from rest_framework import serializers

from .models import (
    Content,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ["id", "title", "description", "status"]
        read_only_fields = ["id", "status"]

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class ContentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentVersion
        fields = [
            "id",
            "content_id",
            "version_number",
            "status",
            "version_notes",
            "created_at",
            "published_at",
            "archived_at",
        ]
        read_only_fields = fields


class ContentVersionCreateSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    version_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ["id", "name", "description", "status"]
        read_only_fields = ["id", "status"]

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class ContentAssignmentCreateSerializer(serializers.Serializer):
    content_id = serializers.UUIDField()

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)


class ContentAssignmentSerializer(serializers.ModelSerializer):
    program_id = serializers.UUIDField(read_only=True)
    content_id = serializers.UUIDField(read_only=True)
    content_title = serializers.CharField(source="content.title", read_only=True)
    content_status = serializers.CharField(source="content.status", read_only=True)

    class Meta:
        model = ContentAssignment
        fields = [
            "program_id",
            "content_id",
            "content_title",
            "content_status",
        ]
        read_only_fields = fields


class ProgramAccessGrantCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    program_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError(
                "The expiration time must be in the future."
            )
        return value


class ContentAccessCreateSerializer(serializers.Serializer):
    program_id = serializers.UUIDField()

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected_fields = set(data.keys()) - set(self.fields)
            if unexpected_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unexpected field."]
                        for field in sorted(unexpected_fields)
                    }
                )
        return super().to_internal_value(data)


class ProgramAccessGrantSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    user_id = serializers.UUIDField(read_only=True)
    program_id = serializers.UUIDField(read_only=True)
    granted_by_id = serializers.UUIDField(read_only=True)
    revoked_by_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = ProgramAccessGrant
        fields = [
            "id",
            "user_id",
            "program_id",
            "status",
            "granted_at",
            "granted_by_id",
            "revoked_at",
            "revoked_by_id",
            "expires_at",
        ]
        read_only_fields = fields

    def get_status(self, grant):
        if (
            grant.status == ProgramAccessGrant.Status.ACTIVE
            and grant.expires_at is not None
            and grant.expires_at <= timezone.now()
        ):
            return ProgramAccessGrant.Status.EXPIRED
        return grant.status
