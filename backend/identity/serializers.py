from rest_framework import serializers


from rest_framework import serializers

from accountability.models import AuditRecord

from .models import Permission, Role, User
from .rbac import assign_role


class LoginSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class UserSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    status = serializers.CharField(source="status", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "status", "roles"]
        read_only_fields = fields

    def get_name(self, user):
        return " ".join(part for part in (user.first_name, user.last_name) if part)

    def get_roles(self, user):
        return list(
            user.user_roles.filter(
                organization_id=user.organization_id,
                role__organization_id=user.organization_id,
            )
            .order_by("role__name")
            .values_list("role__name", flat=True)
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["status"] = instance.status.lower()
        return data


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=301, trim_whitespace=True)
    email = serializers.EmailField()
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Role.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["role_ids"].queryset = Role.objects.filter(
                organization_id=request.user.organization_id
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

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_email(self, value):
        request = self.context["request"]
        email = User.objects.normalize_email(value)
        if User.objects.filter(
            organization_id=request.user.organization_id,
            email=email,
        ).exists():
            raise serializers.ValidationError(
                "A user with this email already exists in the organization."
            )
        return email

    def validate_role_ids(self, roles):
        role_ids = [role.id for role in roles]
        if len(role_ids) != len(set(role_ids)):
            raise serializers.ValidationError("Duplicate roles are not allowed.")
        return roles

    def create(self, validated_data):
        import secrets

        request = self.context["request"]
        roles = validated_data.pop("role_ids", [])
        name = validated_data.pop("name")
        first_name, _, last_name = name.partition(" ")
        temporary_password = secrets.token_urlsafe(24)
        user = User.objects.create_user(
            email=validated_data["email"],
            password=temporary_password,
            organization=request.user.organization,
            first_name=first_name,
            last_name=last_name,
        )
        user._temporary_password = temporary_password

        AuditRecord.objects.create(
            organization_id=user.organization_id,
            actor_user=request.user,
            action=AuditRecord.Action.USER_CREATED,
            resource_type="user",
            resource_id=user.id,
            new_values={
                "email": user.email,
                "name": name,
                "status": user.status.lower(),
            },
        )
        for role in roles:
            assign_role(user, role, assigned_by=request.user)
        return user


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=301, trim_whitespace=True, required=False)
    status = serializers.ChoiceField(
        choices=[("active", "active"), ("inactive", "inactive")],
        required=False,
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
        if not data:
            raise serializers.ValidationError("At least one field is required.")
        return super().to_internal_value(data)

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def update(self, instance, validated_data):
        old_values = {
            "name": " ".join(
                part for part in (instance.first_name, instance.last_name) if part
            ),
            "status": instance.status.lower(),
        }
        if "name" in validated_data:
            first_name, _, last_name = validated_data["name"].partition(" ")
            instance.first_name = first_name
            instance.last_name = last_name
        if "status" in validated_data:
            instance.status = validated_data["status"].upper()
        instance.save(update_fields=["first_name", "last_name", "status", "updated_at"])
        new_values = {
            "name": " ".join(
                part for part in (instance.first_name, instance.last_name) if part
            ),
            "status": instance.status.lower(),
        }
        changed_old = {
            key: value for key, value in old_values.items() if value != new_values[key]
        }
        changed_new = {key: new_values[key] for key in changed_old}
        if changed_new:
            AuditRecord.objects.create(
                organization_id=instance.organization_id,
                actor_user=self.context["request"].user,
                action=AuditRecord.Action.USER_UPDATED,
                resource_type="user",
                resource_id=instance.id,
                old_values=changed_old,
                new_values=changed_new,
            )
        return instance


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name"]
        read_only_fields = fields


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["code", "name"]
        read_only_fields = fields