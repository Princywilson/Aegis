import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"

    def __str__(self):
        return self.name


class Permission(models.Model):
    class Code(models.TextChoices):
        PROFILE_VIEW_OWN = "PROFILE_VIEW_OWN", "View own profile"
        PROFILE_UPDATE_OWN = "PROFILE_UPDATE_OWN", "Update own profile"
        USER_VIEW = "USER_VIEW", "View users"
        USER_CREATE = "USER_CREATE", "Create users"
        USER_UPDATE = "USER_UPDATE", "Update users"
        USER_DEACTIVATE = "USER_DEACTIVATE", "Deactivate users"
        ROLE_MANAGE = "ROLE_MANAGE", "Manage roles"
        CONTENT_VIEW = "CONTENT_VIEW", "View content"
        CONTENT_SEARCH = "CONTENT_SEARCH", "Search content"
        CONTENT_CREATE = "CONTENT_CREATE", "Create content"
        CONTENT_UPDATE = "CONTENT_UPDATE", "Update content"
        CONTENT_ARCHIVE = "CONTENT_ARCHIVE", "Archive content"
        CONTENT_PUBLISH = "CONTENT_PUBLISH", "Publish content"
        VERSION_VIEW = "VERSION_VIEW", "View content versions"
        VERSION_CREATE = "VERSION_CREATE", "Create content versions"
        VERSION_PUBLISH = "VERSION_PUBLISH", "Publish content versions"
        VERSION_ARCHIVE = "VERSION_ARCHIVE", "Archive content versions"
        PROGRAM_VIEW = "PROGRAM_VIEW", "View programs"
        PROGRAM_CREATE = "PROGRAM_CREATE", "Create programs"
        PROGRAM_UPDATE = "PROGRAM_UPDATE", "Update programs"
        ASSIGNMENT_MANAGE = "ASSIGNMENT_MANAGE", "Manage content assignments"
        ACCESS_GRANT = "ACCESS_GRANT", "Grant content access"
        ACCESS_REVOKE = "ACCESS_REVOKE", "Revoke content access"
        SECURE_DELIVERY = "SECURE_DELIVERY", "Use secure content delivery"
        WATERMARK_CONSUME = "WATERMARK_CONSUME", "Consume watermarked content"
        ACTIVITY_VIEW_OWN = "ACTIVITY_VIEW_OWN", "View own activity"
        ACTIVITY_VIEW_ORGANIZATION = (
            "ACTIVITY_VIEW_ORGANIZATION",
            "View organization activity",
        )
        AUDIT_VIEW_ORGANIZATION = (
            "AUDIT_VIEW_ORGANIZATION",
            "View organization audit records",
        )
        SECURITY_EVENT_VIEW_ORGANIZATION = (
            "SECURITY_EVENT_VIEW_ORGANIZATION",
            "View organization security events",
        )
        REPORT_VIEW_ASSIGNED = (
            "REPORT_VIEW_ASSIGNED",
            "View reports for assigned resources",
        )
        REPORT_VIEW_ORGANIZATION = (
            "REPORT_VIEW_ORGANIZATION",
            "View organization reports",
        )
        ANALYTICS_VIEW_ASSIGNED = (
            "ANALYTICS_VIEW_ASSIGNED",
            "View analytics for assigned resources",
        )
        ANALYTICS_VIEW_ORGANIZATION = (
            "ANALYTICS_VIEW_ORGANIZATION",
            "View organization analytics",
        )
        CONFIGURATION_MANAGE = "CONFIGURATION_MANAGE", "Manage organization configuration"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, choices=Code.choices, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permissions"
        ordering = ["code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="roles",
    )
    code = models.SlugField(max_length=100)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="roles",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_role_code_per_organization",
            ),
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_role_name_per_organization",
            ),
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.PROTECT,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            ),
        ]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not extra_fields.get("organization"):
            raise ValueError("An organization is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)

        if not extra_fields["is_staff"]:
            raise ValueError("A superuser must have is_staff=True.")
        if not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    last_login = models.DateTimeField(
        blank=True,
        null=True,
        db_column="last_login_at",
        verbose_name="last login",
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["organization"]

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_user_email_per_organization",
            ),
        ]

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return self.email


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="user_roles",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="user_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="role_assignments_made",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "user_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "role"],
                name="unique_user_role_per_organization",
            ),
        ]

    def clean(self):
        errors = {}
        if self.user_id and self.organization_id:
            if self.user.organization_id != self.organization_id:
                errors["user"] = "The user must belong to the selected organization."
        if self.role_id and self.organization_id:
            if self.role.organization_id != self.organization_id:
                errors["role"] = "The role must belong to the selected organization."
        if self.assigned_by_id and self.organization_id:
            if self.assigned_by.organization_id != self.organization_id:
                errors["assigned_by"] = (
                    "The assigning user must belong to the selected organization."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)