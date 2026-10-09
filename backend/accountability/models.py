import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


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