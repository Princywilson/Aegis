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
