from datetime import datetime, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.serializers import DateTimeField, UUIDField
from rest_framework.views import APIView

from identity.models import Permission
from identity.permissions import HasAegisPermission, has_permission
from knowledge.authentication import ApiSessionAuthentication
from knowledge.risk_signals import build_risk_signals_for_organization, summarize_risk_signals

from .evidence import validate_evidence_references
from .models import ActivityEvent, AuditRecord, RiskInvestigation, SecurityEvent
from .serializers import (
    ActivityEventSerializer,
    AuditRecordSerializer,
    RiskInvestigationSerializer,
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
        return queryset.order_by("-occurred_at")

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


class RiskSignalListView(APIView):
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    required_aegis_permission = Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        options = _parse_risk_signal_options(request, include_pagination=True)
        signals = build_risk_signals_for_organization(
            request.user.organization_id,
            start=options["start"],
            end=options["end"],
        )
        signals = _filter_risk_signals(signals, options)
        page = options["page"]
        page_size = options["page_size"]
        start_index = (page - 1) * page_size
        return Response(
            {
                "data": signals[start_index : start_index + page_size],
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(signals),
                },
            }
        )


class RiskSignalSummaryView(APIView):
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    required_aegis_permission = Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        options = _parse_risk_signal_options(request, include_pagination=False)
        signals = build_risk_signals_for_organization(
            request.user.organization_id,
            start=options["start"],
            end=options["end"],
        )
        signals = _filter_risk_signals(signals, options)
        return Response({"data": summarize_risk_signals(signals)})


def _parse_risk_signal_options(request, *, include_pagination):
    allowed = {"from", "to", "user_id", "severity", "signal_type"}
    if include_pagination:
        allowed |= {"page", "page_size"}
    unknown = set(request.query_params) - allowed
    if unknown:
        raise ValidationError(
            {key: ["Unexpected query parameter."] for key in sorted(unknown)}
        )

    start = _parse_signal_datetime(request, "from")
    end = _parse_signal_datetime(request, "to")
    end = end or timezone.now()
    start = start or end - timedelta(hours=24)
    if start > end:
        raise ValidationError({"from": ["Must be earlier than or equal to 'to'."]})

    user_id = None
    if "user_id" in request.query_params:
        try:
            user_id = UUIDField().run_validation(request.query_params["user_id"])
        except ValidationError as exc:
            raise ValidationError({"user_id": exc.detail}) from exc

    severity = request.query_params.get("severity")
    if severity is not None:
        severity = severity.upper()
        if severity not in {"LOW", "MEDIUM"}:
            raise ValidationError({"severity": ["Select a valid signal severity."]})

    signal_type = request.query_params.get("signal_type")
    if signal_type is not None:
        signal_type = signal_type.upper()
        if signal_type not in {"ACCESS_BURST", "REPEATED_DENIALS"}:
            raise ValidationError({"signal_type": ["Select a valid signal type."]})

    options = {
        "start": start,
        "end": end,
        "user_id": str(user_id) if user_id is not None else None,
        "severity": severity,
        "signal_type": signal_type,
    }
    if include_pagination:
        options["page"] = _parse_positive_integer(request, "page", default=1)
        options["page_size"] = _parse_positive_integer(
            request,
            "page_size",
            default=20,
        )
        if options["page_size"] > 100:
            raise ValidationError({"page_size": ["Must be at most 100."]})
    return options


def _parse_signal_datetime(request, parameter):
    if parameter not in request.query_params:
        return None
    value = request.query_params[parameter]
    try:
        provided_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {parameter: ["Enter a valid ISO-8601 datetime with a timezone."]}
        ) from exc
    if timezone.is_naive(provided_datetime):
        raise ValidationError(
            {parameter: ["A timezone-aware datetime is required."]}
        )
    try:
        return DateTimeField().run_validation(value)
    except ValidationError as exc:
        raise ValidationError({parameter: exc.detail}) from exc


def _parse_positive_integer(request, parameter, *, default):
    if parameter not in request.query_params:
        return default
    value = request.query_params[parameter]
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({parameter: ["A valid integer is required."]}) from exc
    if parsed < 1:
        raise ValidationError({parameter: ["Must be a positive integer."]})
    return parsed


def _filter_risk_signals(signals, options):
    if options["user_id"] is not None:
        signals = [signal for signal in signals if signal["user_id"] == options["user_id"]]
    if options["severity"] is not None:
        signals = [
            signal for signal in signals if signal["severity"] == options["severity"]
        ]
    if options["signal_type"] is not None:
        signals = [
            signal for signal in signals if signal["type"] == options["signal_type"]
        ]
    return signals


class RiskInvestigationListCreateView(APIView):
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    required_aegis_permission = Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request):
        allowed = {"page", "page_size", "status", "severity"}
        unknown = set(request.query_params) - allowed
        if unknown:
            raise ValidationError(
                {key: ["Unexpected query parameter."] for key in sorted(unknown)}
            )

        queryset = RiskInvestigation.objects.filter(
            organization_id=request.user.organization_id
        ).select_related("created_by", "reviewed_by")
        status = request.query_params.get("status")
        if status is not None:
            status = status.upper()
            if status not in RiskInvestigation.Status.values:
                raise ValidationError({"status": ["Select a valid status."]})
            queryset = queryset.filter(status=status)
        severity = request.query_params.get("severity")
        if severity is not None:
            severity = severity.upper()
            if severity not in RiskInvestigation.Severity.values:
                raise ValidationError({"severity": ["Select a valid severity."]})
            queryset = queryset.filter(severity=severity)

        _parse_positive_integer(request, "page", default=1)
        page_size = _parse_positive_integer(request, "page_size", default=50)
        if page_size > 100:
            raise ValidationError({"page_size": ["Must be at most 100."]})
        paginator = AccountabilityPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RiskInvestigationSerializer(
            page,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        data = _validate_investigation_payload(
            request.data,
            allowed={"title", "summary", "severity", "notes", "evidence"},
        )
        title = _investigation_text(data, "title", required=True, strip=True)
        if len(title) > 255:
            raise ValidationError(
                {"title": ["Ensure this field has no more than 255 characters."]}
            )
        summary = _investigation_text(data, "summary", default="")
        notes = _investigation_text(data, "notes", default="")
        severity = _investigation_choice(
            data,
            "severity",
            RiskInvestigation.Severity.values,
            default=RiskInvestigation.Severity.MEDIUM,
        )
        evidence = validate_evidence_references(
            data.get("evidence", []),
            user=request.user,
            organization_id=request.user.organization_id,
        )
        changed_fields = ["severity", "title"]
        if "summary" in data:
            changed_fields.append("summary")
        if "notes" in data:
            changed_fields.append("notes")
        if evidence:
            changed_fields.append("evidence")

        with transaction.atomic():
            investigation = RiskInvestigation.objects.create(
                organization_id=request.user.organization_id,
                created_by=request.user,
                title=title,
                summary=summary,
                notes=notes,
                severity=severity,
                evidence=evidence,
            )
            AuditRecord.objects.create(
                organization_id=request.user.organization_id,
                actor_user=request.user,
                action=AuditRecord.Action.RISK_INVESTIGATION_CREATED,
                resource_type="risk_investigation",
                resource_id=investigation.id,
                new_values={
                    "status": investigation.status,
                    "severity": investigation.severity,
                },
                metadata={"changed_fields": sorted(changed_fields)},
            )
        serializer = RiskInvestigationSerializer(
            investigation,
            context={"request": request},
        )
        return Response({"data": serializer.data}, status=201)


def _validate_investigation_payload(data, *, allowed):
    if not isinstance(data, dict):
        raise ValidationError({"detail": ["Expected a JSON object."]})
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(
            {key: ["Unexpected field."] for key in sorted(unknown)}
        )
    return data


def _investigation_text(data, field, *, default=None, required=False, strip=False):
    if field not in data:
        if required:
            raise ValidationError({field: ["This field is required."]})
        return default
    value = data[field]
    if not isinstance(value, str):
        raise ValidationError({field: ["A string value is required."]})
    if strip:
        value = value.strip()
    if required and not value:
        raise ValidationError({field: ["This field is required."]})
    return value


def _investigation_choice(data, field, choices, *, default=None):
    if field not in data:
        if default is None:
            raise ValidationError({field: ["This field is required."]})
        return default
    value = data[field]
    if not isinstance(value, str):
        raise ValidationError({field: ["Select a valid choice."]})
    normalized = value.upper()
    if normalized not in choices:
        raise ValidationError({field: ["Select a valid choice."]})
    return normalized


class RiskInvestigationDetailView(APIView):
    authentication_classes = [ApiSessionAuthentication]
    permission_classes = [HasAegisPermission]
    required_aegis_permission = Permission.Code.SECURITY_EVENT_VIEW_ORGANIZATION
    http_method_names = ["get", "patch", "head", "options"]

    def get(self, request, investigation_id):
        investigation = get_object_or_404(
            RiskInvestigation.objects.filter(
                organization_id=request.user.organization_id
            ).select_related("created_by", "reviewed_by"),
            pk=investigation_id,
        )
        serializer = RiskInvestigationSerializer(
            investigation,
            context={"request": request},
        )
        return Response({"data": serializer.data})

    def patch(self, request, investigation_id):
        data = _validate_investigation_payload(
            request.data,
            allowed={"status", "severity", "title", "summary", "notes", "evidence"},
        )
        with transaction.atomic():
            investigation = get_object_or_404(
                RiskInvestigation.objects.select_for_update().filter(
                    organization_id=request.user.organization_id
                ),
                pk=investigation_id,
            )
            old_status = investigation.status
            if old_status in {
                RiskInvestigation.Status.RESOLVED,
                RiskInvestigation.Status.DISMISSED,
            }:
                raise ValidationError(
                    {"detail": ["Resolved or dismissed investigations are read-only."]}
                )
            old_severity = investigation.severity
            old_evidence_count = len(investigation.evidence or [])
            changed_fields = set()
            update_fields = set()

            if "status" in data:
                new_status = _investigation_choice(
                    data,
                    "status",
                    RiskInvestigation.Status.values,
                )
                allowed_transitions = {
                    RiskInvestigation.Status.OPEN: {
                        RiskInvestigation.Status.IN_REVIEW,
                        RiskInvestigation.Status.DISMISSED,
                    },
                    RiskInvestigation.Status.IN_REVIEW: {
                        RiskInvestigation.Status.RESOLVED,
                        RiskInvestigation.Status.DISMISSED,
                    },
                    RiskInvestigation.Status.RESOLVED: set(),
                    RiskInvestigation.Status.DISMISSED: set(),
                }
                if (
                    new_status != old_status
                    and new_status not in allowed_transitions[old_status]
                ):
                    raise ValidationError(
                        {"status": ["This status transition is not allowed."]}
                    )
                if new_status != old_status:
                    investigation.status = new_status
                    changed_fields.add("status")
                    update_fields.add("status")
                    if new_status == RiskInvestigation.Status.RESOLVED:
                        investigation.resolved_at = timezone.now()
                        update_fields.add("resolved_at")
                    if new_status in {
                        RiskInvestigation.Status.IN_REVIEW,
                        RiskInvestigation.Status.RESOLVED,
                        RiskInvestigation.Status.DISMISSED,
                    }:
                        investigation.reviewed_by = request.user
                        update_fields.add("reviewed_by")

            if "severity" in data:
                severity = _investigation_choice(
                    data,
                    "severity",
                    RiskInvestigation.Severity.values,
                )
                if severity != old_severity:
                    investigation.severity = severity
                    changed_fields.add("severity")
                    update_fields.add("severity")

            for field in ("title", "summary", "notes"):
                if field not in data:
                    continue
                value = _investigation_text(
                    data,
                    field,
                    required=(field == "title"),
                    strip=(field == "title"),
                )
                if field == "title" and len(value) > 255:
                    raise ValidationError(
                        {"title": ["Ensure this field has no more than 255 characters."]}
                    )
                if getattr(investigation, field) != value:
                    setattr(investigation, field, value)
                    changed_fields.add(field)
                    update_fields.add(field)

            if "evidence" in data:
                evidence = validate_evidence_references(
                    data["evidence"],
                    user=request.user,
                    organization_id=request.user.organization_id,
                )
                if evidence != investigation.evidence:
                    investigation.evidence = evidence
                    changed_fields.add("evidence")
                    update_fields.add("evidence")

            if changed_fields:
                update_fields.add("updated_at")
                investigation.save(update_fields=sorted(update_fields))
                action = _investigation_audit_action(
                    investigation.status if "status" in changed_fields else None
                )
                old_values = {}
                new_values = {}
                if "status" in changed_fields:
                    old_values["status"] = old_status
                    new_values["status"] = investigation.status
                if "severity" in changed_fields:
                    old_values["severity"] = old_severity
                    new_values["severity"] = investigation.severity
                AuditRecord.objects.create(
                    organization_id=request.user.organization_id,
                    actor_user=request.user,
                    action=action,
                    resource_type="risk_investigation",
                    resource_id=investigation.id,
                    old_values=old_values or None,
                    new_values=new_values or None,
                    metadata={
                        "changed_fields": sorted(changed_fields),
                        "evidence_count_before": old_evidence_count,
                        "evidence_count_after": len(investigation.evidence or []),
                    },
                )

        serializer = RiskInvestigationSerializer(
            investigation,
            context={"request": request},
        )
        return Response({"data": serializer.data})


def _investigation_audit_action(status):
    if status == RiskInvestigation.Status.RESOLVED:
        return AuditRecord.Action.RISK_INVESTIGATION_RESOLVED
    if status == RiskInvestigation.Status.DISMISSED:
        return AuditRecord.Action.RISK_INVESTIGATION_DISMISSED
    return AuditRecord.Action.RISK_INVESTIGATION_UPDATED
