from datetime import datetime

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accountability.models import ActivityEvent
from identity.models import Permission
from identity.permissions import HasAegisPermission
from identity.rbac import has_permission as user_has_permission
from .authentication import ApiSessionAuthentication
from .models import (
    Content,
    ContentAccess,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)


class ReportingPagination(PageNumberPagination):
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


class ContentAccessReportSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    user_name = serializers.SerializerMethodField()
    content_id = serializers.UUIDField(read_only=True)
    content_title = serializers.CharField(source="content.title", read_only=True)
    content_version_id = serializers.UUIDField(read_only=True)
    version_number = serializers.IntegerField(
        source="content_version.version_number",
        read_only=True,
    )
    program_id = serializers.UUIDField(read_only=True, allow_null=True)
    program_name = serializers.CharField(
        source="program.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ContentAccess
        fields = [
            "id",
            "user_id",
            "user_name",
            "content_id",
            "content_title",
            "content_version_id",
            "version_number",
            "program_id",
            "program_name",
            "accessed_at",
        ]
        read_only_fields = fields

    def get_user_name(self, access):
        return " ".join(
            part for part in (access.user.first_name, access.user.last_name) if part
        ) or None


class ReportingView:
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    organization_permission = None
    assigned_permission = None
    base_query_params = {"from", "to", "content_id", "program_id", "user_id"}
    accept_pagination_params = False

    def get_required_aegis_permission(self, request):
        if user_has_permission(request.user, self.organization_permission):
            return self.organization_permission
        return self.assigned_permission

    def allowed_content_ids(self, request):
        user = request.user
        program_ids = ProgramAccessGrant.objects.filter(
            organization_id=user.organization_id,
            user=user,
            status=ProgramAccessGrant.Status.ACTIVE,
            program__status=Program.Status.ACTIVE,
        ).filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        ).values("program_id")
        return ContentAssignment.objects.filter(
            organization_id=user.organization_id,
            program_id__in=program_ids,
            content__status=Content.Status.PUBLISHED,
            content__current_version__status=ContentVersion.Status.PUBLISHED,
        ).values("content_id")

    def access_queryset(self):
        user = self.request.user
        queryset = ContentAccess.objects.filter(
            organization_id=user.organization_id,
            access_result=ContentAccess.Result.GRANTED,
            access_context=ContentAccess.Context.CONSUMER,
        )
        if not user_has_permission(user, self.organization_permission):
            queryset = queryset.filter(
                user=user,
                program_id__in=ProgramAccessGrant.objects.filter(
                    organization_id=user.organization_id,
                    user=user,
                    status=ProgramAccessGrant.Status.ACTIVE,
                    program__status=Program.Status.ACTIVE,
                ).filter(
                    Q(expires_at__isnull=True)
                    | Q(expires_at__gt=timezone.now())
                ).values("program_id"),
                content_id__in=self.allowed_content_ids(self.request),
            )
        return queryset

    def parse_datetime(self, parameter):
        raw_value = self.request.query_params.get(parameter)
        if raw_value is None:
            return None
        try:
            value = serializers.DateTimeField().run_validation(raw_value)
        except ValidationError as exc:
            raise ValidationError({parameter: exc.detail}) from exc
        try:
            provided_datetime = datetime.fromisoformat(
                raw_value.replace("Z", "+00:00")
            )
        except ValueError:
            provided_datetime = None
        if (
            provided_datetime is None
            or timezone.is_naive(provided_datetime)
            or timezone.is_naive(value)
        ):
            raise ValidationError(
                {parameter: ["A timezone-aware datetime is required."]}
            )
        return value

    def parse_uuid(self, parameter):
        raw_value = self.request.query_params.get(parameter)
        if raw_value is None:
            return None
        try:
            return serializers.UUIDField().run_validation(raw_value)
        except ValidationError as exc:
            raise ValidationError({parameter: exc.detail}) from exc

    def filtered_accesses(self):
        allowed_params = self.base_query_params
        if self.accept_pagination_params:
            allowed_params = allowed_params | {"page", "page_size"}
        unknown = set(self.request.query_params) - allowed_params
        if unknown:
            raise ValidationError(
                {
                    name: ["Unexpected query parameter."]
                    for name in sorted(unknown)
                }
            )

        start = self.parse_datetime("from")
        end = self.parse_datetime("to")
        if start is not None and end is not None and start > end:
            raise ValidationError(
                {"from": ["Must be earlier than or equal to 'to'."]}
            )

        queryset = self.access_queryset()
        if start is not None:
            queryset = queryset.filter(accessed_at__gte=start)
        if end is not None:
            queryset = queryset.filter(accessed_at__lte=end)
        content_id = self.parse_uuid("content_id")
        if content_id is not None:
            queryset = queryset.filter(content_id=content_id)
        program_id = self.parse_uuid("program_id")
        if program_id is not None:
            queryset = queryset.filter(program_id=program_id)
        requested_user_id = self.parse_uuid("user_id")
        if requested_user_id is not None:
            queryset = queryset.filter(user_id=requested_user_id)
        return queryset, start, end


class ContentAnalyticsView(ReportingView, generics.GenericAPIView):
    organization_permission = Permission.Code.ANALYTICS_VIEW_ORGANIZATION
    assigned_permission = Permission.Code.ANALYTICS_VIEW_ASSIGNED

    def get(self, request):
        accesses, start, end = self.filtered_accesses()
        most_viewed = (
            accesses.values("content_id", "content__title")
            .annotate(view_count=Count("id"))
            .order_by("-view_count", "content_id")
            .first()
        )
        access_frequency = (
            accesses.annotate(day=TruncDate("accessed_at"))
            .values("day")
            .annotate(views=Count("id"))
            .order_by("day")
        )
        version_usage = (
            accesses.values(
                "content_id",
                "content__title",
                "content_version_id",
                "content_version__version_number",
            )
            .annotate(views=Count("id"))
            .order_by("content_id", "content_version__version_number")
        )
        activity = ActivityEvent.objects.filter(
            organization_id=request.user.organization_id,
            content_id__in=accesses.values("content_id"),
            content_access__access_context=ContentAccess.Context.CONSUMER,
        )
        if not user_has_permission(
            request.user,
            Permission.Code.ANALYTICS_VIEW_ORGANIZATION,
        ):
            activity = activity.filter(user=request.user)
        if start is not None:
            activity = activity.filter(occurred_at__gte=start)
        if end is not None:
            activity = activity.filter(occurred_at__lte=end)

        return Response(
            {
                "data": {
                    "total_views": accesses.count(),
                    "active_users": accesses.values("user_id").distinct().count(),
                    "most_viewed_content": (
                        {
                            "content_id": str(most_viewed["content_id"]),
                            "title": most_viewed["content__title"],
                            "views": most_viewed["view_count"],
                        }
                        if most_viewed
                        else None
                    ),
                    "access_frequency": [
                        {
                            "date": row["day"].isoformat(),
                            "views": row["views"],
                        }
                        for row in access_frequency
                    ],
                    "version_usage": [
                        {
                            "content_id": str(row["content_id"]),
                            "content_title": row["content__title"],
                            "content_version_id": str(row["content_version_id"]),
                            "version_number": row[
                                "content_version__version_number"
                            ],
                            "views": row["views"],
                        }
                        for row in version_usage
                    ],
                    "recent_activity": [
                        {
                            "id": str(row["id"]),
                            "event_type": row["event_type"],
                            "occurred_at": row["occurred_at"].isoformat(),
                            "content_title": row["content__title"],
                            "user_name": " ".join(
                                part
                                for part in (
                                    row["user__first_name"],
                                    row["user__last_name"],
                                )
                                if part
                            ) or None,
                            "program_name": row["program__name"],
                        }
                        for row in activity.order_by(
                            "-occurred_at",
                        ).values(
                            "id",
                            "event_type",
                            "occurred_at",
                            "content__title",
                            "user__first_name",
                            "user__last_name",
                            "program__name",
                        )[:10]
                    ],
                }
            }
        )


class ContentAccessReportView(ReportingView, generics.GenericAPIView):
    organization_permission = Permission.Code.REPORT_VIEW_ORGANIZATION
    assigned_permission = Permission.Code.REPORT_VIEW_ASSIGNED
    pagination_class = ReportingPagination
    serializer_class = ContentAccessReportSerializer
    accept_pagination_params = True

    def get(self, request):
        queryset, _, _ = self.filtered_accesses()
        queryset = queryset.select_related(
            "user",
            "content",
            "content_version",
            "program",
        ).order_by("-accessed_at", "id")
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
