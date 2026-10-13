from datetime import datetime

from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.serializers import DateTimeField, UUIDField

from identity.models import Permission
from identity.permissions import HasAegisPermission, has_permission
from knowledge.authentication import ApiSessionAuthentication

from .models import ActivityEvent, AuditRecord, SecurityEvent
from .serializers import (
    ActivityEventSerializer,
    AuditRecordSerializer,
    SecurityEventSerializer,
)


class AccountabilityPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "meta": {
                    "page": self.page.number,
                    "page_size": self.page.paginator.per_page,
                    "total": self.page.paginator.count,
                },
            }
        )


class FilterableOrganizationListView(generics.ListAPIView):
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    pagination_class = AccountabilityPagination
    allowed_query_params = {"page", "page_size", "from", "to"}

    def filter_time_range(self, queryset):
        start = self._parse_datetime("from")
        end = self._parse_datetime("to")
        if start is not None and end is not None and start > end:
            raise ValidationError(
                {"from": ["Must be earlier than or equal to 'to'."]}
            )
        if start is not None:
            queryset = queryset.filter(occurred_at__gte=start)
        if end is not None:
            queryset = queryset.filter(occurred_at__lte=end)
        return queryset.order_by("-occurred_at", "id")

    def _parse_datetime(self, parameter):
        value = self.request.query_params.get(parameter)
        if value is None:
            return None
        try:
            parsed = DateTimeField().run_validation(value)
        except ValidationError as exc:
            raise ValidationError({parameter: exc.detail}) from exc
        try:
            provided_datetime = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            provided_datetime = None
        if (
            provided_datetime is None
            or timezone.is_naive(provided_datetime)
            or timezone.is_naive(parsed)
        ):
            raise ValidationError(
                {parameter: ["A timezone-aware datetime is required."]}
            )
        return parsed

    def parse_uuid(self, parameter):
        value = self.request.query_params.get(parameter)
        if value is None:
            return None
        try:
            return UUIDField().run_validation(value)
        except ValidationError as exc:
            raise ValidationError({parameter: exc.detail}) from exc

    def validate_query_params(self):
        unknown = set(self.request.query_params) - self.allowed_query_params
        if unknown:
            raise ValidationError(
                {
                    name: ["Unexpected query parameter."]
                    for name in sorted(unknown)
                }
            )


class ActivityEventListView(FilterableOrganizationListView):
    serializer_class = ActivityEventSerializer

    @classmethod
    def permission_for(cls, request):
        if has_permission(
            request.user,
            Permission.Code.ACTIVITY_VIEW_ORGANIZATION,
        ):
            return Permission.Code.ACTIVITY_VIEW_ORGANIZATION
        return Permission.Code.ACTIVITY_VIEW_OWN

    def get_required_aegis_permission(self, request):
        return self.permission_for(request)

    def get_queryset(self):
        self.validate_query_params()
        queryset = ActivityEvent.objects.filter(
            organization_id=self.request.user.organization_id,
        ).select_related(
            "user",
            "content",
            "content_version",
            "program",
            "content_access",
        )
        if not has_permission(
            self.request.user,
            Permission.Code.ACTIVITY_VIEW_ORGANIZATION,
        ):
            queryset = queryset.filter(user=self.request.user)

        user_id = self.parse_uuid("user_id")
        content_id = self.parse_uuid("content_id")
        event_type = self.request.query_params.get("event_type")
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        if content_id is not None:
            queryset = queryset.filter(content_id=content_id)
        if event_type:
            if event_type not in ActivityEvent.EventType.values:
                raise ValidationError(
                    {"event_type": ["Select a valid activity event type."]}
                )
            queryset = queryset.filter(event_type=event_type)
        return self.filter_time_range(queryset)

    @property
    def allowed_query_params(self):
        return super().allowed_query_params | {
            "user_id",
            "content_id",
            "event_type",
        }


class AuditRecordListView(FilterableOrganizationListView):
    serializer_class = AuditRecordSerializer
    required_aegis_permission = Permission.Code.AUDIT_VIEW_ORGANIZATION

    def get_queryset(self):
        self.validate_query_params()
        queryset = AuditRecord.objects.filter(
            organization_id=self.request.user.organization_id,
        ).select_related("actor_user")

        actor_id = self.parse_uuid("actor_id")
        resource_id = self.parse_uuid("resource_id")
        action = self.request.query_params.get("action")
        resource_type = self.request.query_params.get("resource_type")
        if actor_id is not None:
            queryset = queryset.filter(actor_user_id=actor_id)
        if resource_id is not None:
            queryset = queryset.filter(resource_id=resource_id)
        if action:
            if action not in AuditRecord.Action.values:
                raise ValidationError({"action": ["Select a valid action."]})
            queryset = queryset.filter(action=action)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        return self.filter_time_range(queryset)

    @property
    def allowed_query_params(self):
        return super().allowed_query_params | {
            "actor_id",
            "action",
            "resource_type",
            "resource_id",
        }


class SecurityEventListView(FilterableOrganizationListView):
    serializer_class = SecurityEventSerializer
    required_aegis_permission = Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION

    def get_queryset(self):
        self.validate_query_params()
        queryset = SecurityEvent.objects.filter(
            organization_id=self.request.user.organization_id,
        ).select_related("user")

        severity = self.request.query_params.get("severity")
        event_type = self.request.query_params.get("event_type")
        if severity:
            if severity not in SecurityEvent.Severity.values:
                raise ValidationError(
                    {"severity": ["Select a valid severity."]}
                )
            queryset = queryset.filter(severity=severity)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return self.filter_time_range(queryset)

    @property
    def allowed_query_params(self):
        return super().allowed_query_params | {"severity", "event_type"}
