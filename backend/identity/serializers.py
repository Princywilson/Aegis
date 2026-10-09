from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)