from rest_framework import serializers

from .models import Content, ContentVersion


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
