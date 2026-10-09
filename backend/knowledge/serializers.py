from rest_framework import serializers

from .models import Content


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
