import uuid
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .storage import StorageService


class Content(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="contents",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    current_version = models.ForeignKey(
        "knowledge.ContentVersion",
        on_delete=models.SET_NULL,
        related_name="current_for_contents",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_contents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contents"
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(
                fields=["organization"],
                name="contents_org_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="contents_org_status_idx",
            ),
        ]

    def __str__(self):
        return self.title


class ContentVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="content_versions",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    version_notes = models.TextField(blank=True)
    storage_key = models.CharField(max_length=512)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_content_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "content_versions"
        ordering = ["content_id", "version_number"]
        indexes = [
            models.Index(
                fields=["organization", "content"],
                name="cntver_org_content_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "content", "version_number"],
                name="unique_version_number_per_content",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gt=0),
                name="content_version_number_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "PUBLISHED", "ARCHIVED"]),
                name="content_version_status_valid",
            ),
        ]

    def clean(self):
        if (
            self.content_id
            and self.organization_id
            and self.content.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"organization": "Must match the content organization."}
            )
        if self.organization_id and self.content_id and self.pk:
            expected_storage_key = StorageService.build_storage_key(
                organization_id=self.organization_id,
                content_id=self.content_id,
                version_id=self.pk,
            )
            if self.storage_key != expected_storage_key:
                raise ValidationError(
                    {"storage_key": "Must match this version's internal storage key."}
                )
        if self.file_size == 0:
            raise ValidationError({"file_size": "Uploaded files cannot be empty."})
        if not re.fullmatch(r"[0-9a-f]{64}", self.checksum or ""):
            raise ValidationError({"checksum": "Must be a lowercase SHA-256 digest."})

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values(
                "status",
                "organization_id",
                "content_id",
                "version_number",
                "version_notes",
                "storage_key",
                "original_filename",
                "mime_type",
                "file_size",
                "checksum",
                "created_by_id",
                "created_at",
            ).first()
            if previous and previous["status"] in {
                self.Status.PUBLISHED,
                self.Status.ARCHIVED,
            }:
                immutable_fields = (
                    "organization_id",
                    "content_id",
                    "version_number",
                    "version_notes",
                    "storage_key",
                    "original_filename",
                    "mime_type",
                    "file_size",
                    "checksum",
                    "created_by_id",
                    "created_at",
                )
                if any(
                    getattr(self, field) != previous[field]
                    for field in immutable_fields
                ):
                    raise ValidationError(
                        "Published content version data is immutable."
                    )
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.content_id}:v{self.version_number}"


class Program(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="programs",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_programs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "programs"
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["organization"], name="program_org_idx"),
            models.Index(
                fields=["organization", "status"],
                name="program_org_status_idx",
            ),
        ]

    def clean(self):
        if (
            self.organization_id
            and self.created_by_id
            and self.created_by.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"created_by": "Must belong to the program organization."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ContentAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="content_assignments",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="content_assignments",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.PROTECT,
        related_name="program_assignments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_content_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_assignments"
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "content"],
                name="unique_program_content_assignment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "program"],
                name="assign_org_program_idx",
            ),
            models.Index(
                fields=["organization", "content"],
                name="assign_org_content_idx",
            ),
        ]

    def clean(self):
        if self.organization_id and self.program_id:
            if self.program.organization_id != self.organization_id:
                raise ValidationError(
                    {"program": "Must belong to the assignment organization."}
                )
        if self.organization_id and self.content_id:
            if self.content.organization_id != self.organization_id:
                raise ValidationError(
                    {"content": "Must belong to the assignment organization."}
                )
        if self.organization_id and self.created_by_id:
            if self.created_by.organization_id != self.organization_id:
                raise ValidationError(
                    {"created_by": "Must belong to the assignment organization."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.program_id}:{self.content_id}"


class ProgramAccessGrant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        REVOKED = "REVOKED", "Revoked"
        EXPIRED = "EXPIRED", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="program_access_grants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="program_access_grants",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="access_grants",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_program_access_grants",
    )
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="revoked_program_access_grants",
        blank=True,
        null=True,
    )
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "program_access_grants"
        ordering = ["-granted_at", "id"]
        indexes = [
            models.Index(
                fields=["organization", "user"],
                name="grant_org_user_idx",
            ),
            models.Index(
                fields=["organization", "program"],
                name="grant_org_program_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "program"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_program_grant",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["ACTIVE", "REVOKED", "EXPIRED"]
                ),
                name="program_grant_status_valid",
            ),
        ]

    def clean(self):
        if self.organization_id and self.user_id:
            if self.user.organization_id != self.organization_id:
                raise ValidationError(
                    {"user": "Must belong to the grant organization."}
                )
        if self.organization_id and self.program_id:
            if self.program.organization_id != self.organization_id:
                raise ValidationError(
                    {"program": "Must belong to the grant organization."}
                )
        for field in ("granted_by", "revoked_by"):
            actor_id = getattr(self, f"{field}_id")
            if (
                self.organization_id
                and actor_id
                and getattr(self, field).organization_id != self.organization_id
            ):
                raise ValidationError(
                    {field: "Must belong to the grant organization."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organization_id}:{self.user_id}:{self.program_id}"


class ContentAccess(models.Model):
    class Context(models.TextChoices):
        CONSUMER = "CONSUMER", "Consumer delivery"
        PREVIEW = "PREVIEW", "Privileged preview"

    class Result(models.TextChoices):
        GRANTED = "GRANTED", "Granted"
        DENIED = "DENIED", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="content_accesses",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="content_accesses",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.PROTECT,
        related_name="accesses",
    )
    content_version = models.ForeignKey(
        ContentVersion,
        on_delete=models.PROTECT,
        related_name="accesses",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="content_accesses",
        blank=True,
        null=True,
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    access_result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.GRANTED,
    )
    access_context = models.CharField(
        max_length=20,
        choices=Context.choices,
        default=Context.CONSUMER,
    )

    class Meta:
        db_table = "content_access"
        ordering = ["-accessed_at", "id"]
        indexes = [
            models.Index(
                fields=["organization", "user", "accessed_at"],
                name="cntaccess_org_user_time_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(access_result__in=["GRANTED", "DENIED"]),
                name="content_access_result_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(access_context__in=["CONSUMER", "PREVIEW"]),
                name="content_access_context_valid",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(access_context="PREVIEW")
                    | models.Q(program__isnull=True)
                ),
                name="content_preview_without_program",
            ),
        ]

    def clean(self):
        if self.organization_id and self.user_id:
            if self.user.organization_id != self.organization_id:
                raise ValidationError(
                    {"user": "Must belong to the access organization."}
                )
        for field in ("content", "content_version", "program"):
            resource_id = getattr(self, f"{field}_id")
            if (
                self.organization_id
                and resource_id
                and getattr(self, field).organization_id != self.organization_id
            ):
                raise ValidationError(
                    {field: "Must belong to the access organization."}
                )
        if self.content_id and self.content_version_id:
            if self.content_version.content_id != self.content_id:
                raise ValidationError(
                    {"content_version": "Must belong to the accessed content."}
                )
        if self.access_result == self.Result.GRANTED and self.program_id:
            if not ContentAssignment.objects.filter(
                organization_id=self.organization_id,
                program_id=self.program_id,
                content_id=self.content_id,
            ).exists():
                raise ValidationError(
                    {"program": "The content must be assigned to the program."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
