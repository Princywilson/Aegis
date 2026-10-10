import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit records are append-only.")

    def delete(self):
        raise ValidationError("Audit records are append-only.")


class ActivityEvent(models.Model):
    class EventType(models.TextChoices):
        VIEWER_OPENED = "VIEWER_OPENED", "Viewer opened"
        VIEWER_PAGE_RENDERED = "VIEWER_PAGE_RENDERED", "Viewer page rendered"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="activity_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="activity_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=100, choices=EventType.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)
    content = models.ForeignKey(
        "knowledge.Content",
        on_delete=models.PROTECT,
        related_name="activity_events",
        null=True,
        blank=True,
    )
    content_version = models.ForeignKey(
        "knowledge.ContentVersion",
        on_delete=models.PROTECT,
        related_name="activity_events",
        null=True,
        blank=True,
    )
    program = models.ForeignKey(
        "knowledge.Program",
        on_delete=models.PROTECT,
        related_name="activity_events",
        null=True,
        blank=True,
    )
    content_access = models.ForeignKey(
        "knowledge.ContentAccess",
        on_delete=models.PROTECT,
        related_name="activity_events",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "activity_events"
        ordering = ["-occurred_at", "id"]
        indexes = [
            models.Index(
                fields=["organization", "user", "occurred_at"],
                name="activity_org_user_time_idx",
            ),
            models.Index(
                fields=["organization", "event_type", "occurred_at"],
                name="activity_org_type_time_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(event_type__in=["VIEWER_OPENED", "VIEWER_PAGE_RENDERED"]),
                name="activity_event_type_valid",
            ),
        ]

    def clean(self):
        for field in (
            "user",
            "content",
            "content_version",
            "program",
            "content_access",
        ):
            related_id = getattr(self, f"{field}_id")
            if (
                self.organization_id
                and related_id
                and getattr(self, field).organization_id != self.organization_id
            ):
                raise ValidationError(
                    {field: "Must belong to the activity organization."}
                )
        if self.content_access_id:
            access = self.content_access
            if any(
                (
                    relation_id is not None
                    and getattr(access, f"{field}_id") != relation_id
                )
                for field, relation_id in (
                    ("user", self.user_id),
                    ("content", self.content_id),
                    ("content_version", self.content_version_id),
                    ("program", self.program_id),
                )
            ):
                raise ValidationError(
                    {"content_access": "Activity must match its access record."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SecurityEvent(models.Model):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="security_events",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="security_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)
    resource_type = models.CharField(max_length=100, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "security_events"
        constraints = [
            models.CheckConstraint(
                condition=Q(severity__in=["INFO", "LOW", "MEDIUM", "HIGH"]),
                name="security_event_severity_valid",
            ),
        ]

    def __str__(self):
        return self.event_type


class AuditRecord(models.Model):
    class Action(models.TextChoices):
        CONTENT_CREATED = "CONTENT_CREATED", "Content created"
        CONTENT_UPDATED = "CONTENT_UPDATED", "Content updated"
        CONTENT_ARCHIVED = "CONTENT_ARCHIVED", "Content archived"
        CONTENT_VERSION_CREATED = (
            "CONTENT_VERSION_CREATED",
            "Content version created",
        )
        CONTENT_VERSION_PUBLISHED = (
            "CONTENT_VERSION_PUBLISHED",
            "Content version published",
        )
        CONTENT_VERSION_ARCHIVED = (
            "CONTENT_VERSION_ARCHIVED",
            "Content version archived",
        )
        PROGRAM_ACCESS_GRANTED = (
            "PROGRAM_ACCESS_GRANTED",
            "Program access granted",
        )
        PROGRAM_ACCESS_REVOKED = (
            "PROGRAM_ACCESS_REVOKED",
            "Program access revoked",
        )
        PROGRAM_CREATED = "PROGRAM_CREATED", "Program created"
        PROGRAM_UPDATED = "PROGRAM_UPDATED", "Program updated"
        PROGRAM_ACTIVATED = "PROGRAM_ACTIVATED", "Program activated"
        PROGRAM_DEACTIVATED = "PROGRAM_DEACTIVATED", "Program deactivated"
        CONTENT_ASSIGNED = "CONTENT_ASSIGNED", "Content assigned"
        CONTENT_UNASSIGNED = "CONTENT_UNASSIGNED", "Content unassigned"
        USER_ROLE_CHANGED = "USER_ROLE_CHANGED", "User role changed"
        PERMISSION_CHANGED = "PERMISSION_CHANGED", "Permission changed"
        USER_CREATED = "USER_CREATED", "User created"
        USER_UPDATED = "USER_UPDATED", "User updated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="audit_records",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_records",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100, choices=Action.choices)
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField()
    occurred_at = models.DateTimeField(auto_now_add=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_records"
        indexes = [
            models.Index(
                fields=["organization", "occurred_at"],
                name="audit_org_time_idx",
            ),
            models.Index(
                fields=["organization", "resource_type", "resource_id"],
                name="audit_org_resource_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    action__in=[
                        "CONTENT_CREATED",
                        "CONTENT_UPDATED",
                        "CONTENT_ARCHIVED",
                        "CONTENT_VERSION_CREATED",
                        "CONTENT_VERSION_PUBLISHED",
                        "CONTENT_VERSION_ARCHIVED",
                        "PROGRAM_ACCESS_GRANTED",
                        "PROGRAM_ACCESS_REVOKED",
                        "PROGRAM_CREATED",
                        "PROGRAM_UPDATED",
                        "PROGRAM_ACTIVATED",
                        "PROGRAM_DEACTIVATED",
                        "CONTENT_ASSIGNED",
                        "CONTENT_UNASSIGNED",
                        "USER_ROLE_CHANGED",
                        "PERMISSION_CHANGED",
                        "USER_CREATED",
                        "USER_UPDATED",
                    ]
                ),
                name="audit_action_valid",
            ),
        ]

    objects = AppendOnlyQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit records are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit records are append-only.")

    def __str__(self):
        return self.action


class AuthenticationRateLimitCounter(models.Model):
    class KeyType(models.TextChoices):
        ACCOUNT = "ACCOUNT", "Account"
        SOURCE_IP = "SOURCE_IP", "Source IP"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key_type = models.CharField(max_length=20, choices=KeyType.choices)
    key_hash = models.CharField(max_length=64)
    failure_timestamps = models.JSONField(default=list)
    blocked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "authentication_rate_limit_counters"
        indexes = [
            models.Index(fields=["updated_at"], name="auth_rate_limit_updated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["key_type", "key_hash"],
                name="unique_auth_rate_limit_key",
            ),
            models.CheckConstraint(
                condition=Q(key_type__in=["ACCOUNT", "SOURCE_IP"]),
                name="auth_rate_limit_key_type_valid",
            ),
        ]

    def __str__(self):
        return f"{self.key_type}:{self.key_hash[:12]}"