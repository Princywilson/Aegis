from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from identity.models import Permission, User
from identity.permissions import HasAegisPermission

from .authentication import ApiSessionAuthentication
from .models import (
    Content,
    ContentAccess,
    ContentAssignment,
    ContentVersion,
    Program,
    ProgramAccessGrant,
)
from .serializers import (
    ContentAssignmentCreateSerializer,
    ContentAssignmentSerializer,
    ContentSerializer,
    ContentVersionCreateSerializer,
    ContentVersionSerializer,
    ContentAccessCreateSerializer,
    ProgramAccessGrantCreateSerializer,
    ProgramAccessGrantSerializer,
    ProgramSerializer,
)
from .delivery import (
    apply_dynamic_watermark,
    get_content_access_for_delivery,
    render_content_version,
    start_content_access,
)
from accountability.models import ActivityEvent, AuditRecord
from accountability.services import record_access_denied
from .services import (
    archive_content,
    archive_content_version,
    create_content_assignment,
    create_content_version,
    grant_program_access,
    publish_content_version,
    revoke_program_access,
    remove_content_assignment,
    set_program_status,
)


def user_is_content_consumer_only(user):
    role_codes = set(user.user_roles.values_list("role__code", flat=True))
    return (
        "content_consumer" in role_codes
        and not role_codes.intersection(
            {"administrator", "content_manager", "management"}
        )
    )


def program_queryset_for(user):
    queryset = Program.objects.filter(organization_id=user.organization_id)
    if user_is_content_consumer_only(user):
        now = timezone.now()
        queryset = queryset.filter(
            access_grants__organization_id=user.organization_id,
            access_grants__user=user,
            access_grants__status=ProgramAccessGrant.Status.ACTIVE,
            status=Program.Status.ACTIVE,
        ).filter(
            Q(access_grants__expires_at__isnull=True)
            | Q(access_grants__expires_at__gt=now)
        ).distinct()
    return queryset


def content_queryset_for(user):
    queryset = Content.objects.filter(organization_id=user.organization_id)
    if user_is_content_consumer_only(user):
        queryset = queryset.filter(
            status=Content.Status.PUBLISHED,
            current_version__status=ContentVersion.Status.PUBLISHED,
            program_assignments__organization_id=user.organization_id,
            program_assignments__program__in=program_queryset_for(user),
        ).distinct()
    return queryset


class ContentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        requested_page_size = request.query_params.get(self.page_size_query_param)
        if requested_page_size is None:
            return self.page_size
        try:
            page_size = int(requested_page_size)
        except (TypeError, ValueError):
            raise ValidationError(
                {"page_size": ["A valid integer is required."]}
            )
        if page_size < 1:
            raise ValidationError(
                {"page_size": ["Ensure this value is greater than zero."]}
            )
        return min(page_size, self.max_page_size)

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


class ContentListCreateView(generics.ListCreateAPIView):
    serializer_class = ContentSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    pagination_class = ContentPagination
    http_method_names = ["get", "post", "head", "options"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            response.data = {"data": response.data}
        return response

    def get_required_aegis_permission(self, request):
        if request.method == "POST":
            return Permission.Code.CONTENT_CREATE
        if request.query_params.get("search"):
            return Permission.Code.CONTENT_SEARCH
        return Permission.Code.CONTENT_VIEW

    def get_queryset(self):
        queryset = content_queryset_for(self.request.user)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter not in Content.Status.values:
                raise ValidationError(
                    {"status": ["Select a valid content status."]}
                )
            queryset = queryset.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            search = search.strip()
            if len(search) > 200:
                raise ValidationError(
                    {"search": ["Ensure this field has no more than 200 characters."]}
                )
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
            )

        if "program_id" in self.request.query_params:
            try:
                program_id = self.request.query_params["program_id"]
                program_id = Program._meta.pk.to_python(program_id)
            except (DjangoValidationError, TypeError, ValueError) as exc:
                raise ValidationError(
                    {"program_id": ["A valid program ID is required."]}
                ) from exc
            if not Program.objects.filter(
                pk=program_id,
                organization_id=self.request.user.organization_id,
            ).exists():
                raise NotFound()
            queryset = queryset.filter(
                program_assignments__organization_id=(
                    self.request.user.organization_id
                ),
                program_assignments__program_id=program_id,
            )
        return queryset

    def perform_create(self, serializer):
        content = serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )
        AuditRecord.objects.create(
            organization=self.request.user.organization,
            actor_user=self.request.user,
            action=AuditRecord.Action.CONTENT_CREATED,
            resource_type="content",
            resource_id=content.id,
            new_values={
                "title": content.title,
                "description": content.description,
                "status": content.status,
            },
        )


class ContentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ContentSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        content = self.get_object()
        old_values = {
            "title": content.title,
            "description": content.description,
        }
        response = super().update(request, *args, **kwargs)
        AuditRecord.objects.create(
            organization=request.user.organization,
            actor_user=request.user,
            action=AuditRecord.Action.CONTENT_UPDATED,
            resource_type="content",
            resource_id=content.id,
            old_values=old_values,
            new_values={
                "title": response.data["title"],
                "description": response.data["description"],
            },
        )
        response.data = {"data": response.data}
        return response

    def get_required_aegis_permission(self, request):
        if request.method == "PATCH":
            return Permission.Code.CONTENT_UPDATE
        return Permission.Code.CONTENT_VIEW

    def get_queryset(self):
        return content_queryset_for(self.request.user)


class ContentArchiveView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.CONTENT_ARCHIVE

    def post(self, request, pk):
        try:
            content = archive_content(
                content_id=pk,
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except Content.DoesNotExist:
            raise NotFound()
        return Response(
            {
                "data": {
                    "id": str(content.id),
                    "status": content.status,
                }
            },
            status=status.HTTP_200_OK,
        )


class ContentVersionListView(generics.ListAPIView):
    serializer_class = ContentVersionSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_required_aegis_permission(self, request):
        if request.method == "POST":
            return Permission.Code.VERSION_CREATE
        return Permission.Code.VERSION_VIEW

    def get_queryset(self):
        if not content_queryset_for(self.request.user).filter(
            pk=self.kwargs["content_id"]
        ).exists():
            raise NotFound()
        queryset = ContentVersion.objects.filter(
            organization_id=self.request.user.organization_id,
            content_id=self.kwargs["content_id"],
        )
        if user_is_content_consumer_only(self.request.user):
            queryset = queryset.filter(
                pk__in=Content.objects.filter(
                    pk=self.kwargs["content_id"],
                    organization_id=self.request.user.organization_id,
                ).values("current_version_id")
            )
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response

    def post(self, request, content_id):
        serializer = ContentVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = create_content_version(
                content_id=content_id,
                organization_id=request.user.organization_id,
                actor=request.user,
                uploaded_file=serializer.validated_data["file"],
                version_notes=serializer.validated_data.get("version_notes", ""),
            )
        except Content.DoesNotExist as exc:
            raise NotFound() from exc
        return Response(
            {"data": ContentVersionSerializer(version).data},
            status=status.HTTP_201_CREATED,
        )


class ContentVersionDetailView(generics.RetrieveAPIView):
    serializer_class = ContentVersionSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    http_method_names = ["get", "head", "options"]

    def get_required_aegis_permission(self, request):
        return Permission.Code.VERSION_VIEW

    def get_queryset(self):
        if not content_queryset_for(self.request.user).filter(
            pk=self.kwargs["content_id"]
        ).exists():
            raise NotFound()
        queryset = ContentVersion.objects.filter(
            organization_id=self.request.user.organization_id,
            content_id=self.kwargs["content_id"],
        )
        if user_is_content_consumer_only(self.request.user):
            queryset = queryset.filter(
                pk__in=Content.objects.filter(
                    pk=self.kwargs["content_id"],
                    organization_id=self.request.user.organization_id,
                ).values("current_version_id")
            )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response


class ContentAccessCreateView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.SECURE_DELIVERY
    http_method_names = ["post", "head", "options"]

    def post(self, request, content_id):
        serializer = ContentAccessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            access = start_content_access(
                content_id=content_id,
                program_id=serializer.validated_data["program_id"],
                organization_id=request.user.organization_id,
                user=request.user,
            )
        except ContentAccess.DoesNotExist as exc:
            record_access_denied(
                organization=request.user.organization,
                user=request.user,
                content_id=content_id,
            )
            raise NotFound() from exc
        return Response(
            {
                "data": {
                    "access_id": str(access.id),
                    "content_id": str(access.content_id),
                    "version_id": str(access.content_version_id),
                    "accessed_at": access.accessed_at,
                }
            },
            status=status.HTTP_201_CREATED,
        )


class ContentDeliveryView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.SECURE_DELIVERY
    http_method_names = ["get", "head", "options"]

    def get(self, request, content_id, access_id):
        try:
            page_number = int(request.query_params.get("page", "1"))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                {"page": ["A valid positive integer is required."]}
            ) from exc
        if page_number < 1:
            raise ValidationError(
                {"page": ["A valid positive integer is required."]}
            )

        try:
            access = get_content_access_for_delivery(
                access_id=access_id,
                content_id=content_id,
                organization_id=request.user.organization_id,
                user=request.user,
            )
        except ContentAccess.DoesNotExist as exc:
            record_access_denied(
                organization=request.user.organization,
                user=request.user,
                content_id=content_id,
            )
            raise NotFound() from exc

        try:
            rendered = render_content_version(
                access.content_version,
                page_number=page_number,
            )
            rendered = apply_dynamic_watermark(rendered, access)
        except ValueError as exc:
            raise ValidationError({"page": [str(exc)]}) from exc

        ActivityEvent.objects.create(
            organization=request.user.organization,
            user=request.user,
            event_type=ActivityEvent.EventType.VIEWER_PAGE_RENDERED,
            content=access.content,
            content_version=access.content_version,
            program=access.program,
            content_access=access,
            metadata={"page_number": page_number},
        )
        response = HttpResponse(rendered.content, content_type="image/png")
        response["Cache-Control"] = "private, no-store"
        response["Content-Disposition"] = (
            f'inline; filename="content-page-{page_number}.png"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Page-Count"] = str(rendered.page_count)
        return response


class ContentVersionPublishView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.VERSION_PUBLISH

    def post(self, request, content_id, version_id):
        try:
            _, version = publish_content_version(
                content_id=content_id,
                version_id=version_id,
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except (Content.DoesNotExist, ContentVersion.DoesNotExist) as exc:
            raise NotFound() from exc
        return Response(
            {
                "data": {
                    "id": str(version.id),
                    "status": version.status,
                }
            }
        )


class ContentVersionArchiveView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.VERSION_ARCHIVE

    def post(self, request, content_id, version_id):
        try:
            version = archive_content_version(
                content_id=content_id,
                version_id=version_id,
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except (Content.DoesNotExist, ContentVersion.DoesNotExist) as exc:
            raise NotFound() from exc
        return Response(
            {
                "data": {
                    "id": str(version.id),
                    "status": version.status,
                }
            }
        )


class ProgramListCreateView(generics.ListCreateAPIView):
    serializer_class = ProgramSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    pagination_class = ContentPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_required_aegis_permission(self, request):
        if request.method == "POST":
            return Permission.Code.PROGRAM_CREATE
        return Permission.Code.PROGRAM_VIEW

    def get_queryset(self):
        queryset = program_queryset_for(self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter not in Program.Status.values:
                raise ValidationError(
                    {"status": ["Select a valid program status."]}
                )
            queryset = queryset.filter(status=status_filter)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response

    def perform_create(self, serializer):
        program = serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )
        AuditRecord.objects.create(
            organization=self.request.user.organization,
            actor_user=self.request.user,
            action=AuditRecord.Action.PROGRAM_CREATED,
            resource_type="program",
            resource_id=program.id,
            new_values={
                "name": program.name,
                "description": program.description,
                "status": program.status,
            },
        )


class ProgramDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ProgramSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    def get_required_aegis_permission(self, request):
        if request.method == "PATCH":
            return Permission.Code.PROGRAM_UPDATE
        return Permission.Code.PROGRAM_VIEW

    def get_queryset(self):
        return program_queryset_for(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        program = self.get_object()
        old_values = {
            "name": program.name,
            "description": program.description,
        }
        response = super().update(request, *args, **kwargs)
        AuditRecord.objects.create(
            organization=request.user.organization,
            actor_user=request.user,
            action=AuditRecord.Action.PROGRAM_UPDATED,
            resource_type="program",
            resource_id=program.id,
            old_values=old_values,
            new_values={
                "name": response.data["name"],
                "description": response.data["description"],
            },
        )
        response.data = {"data": response.data}
        return response


class ProgramStatusView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.PROGRAM_UPDATE
    target_status = None

    def post(self, request, program_id):
        try:
            program = set_program_status(
                program_id=program_id,
                organization_id=request.user.organization_id,
                status=self.target_status,
                actor=request.user,
            )
        except Program.DoesNotExist as exc:
            raise NotFound() from exc
        return Response({"data": ProgramSerializer(program).data})


class ProgramActivateView(ProgramStatusView):
    target_status = Program.Status.ACTIVE


class ProgramDeactivateView(ProgramStatusView):
    target_status = Program.Status.INACTIVE


class ProgramContentListCreateView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    http_method_names = ["get", "post", "head", "options"]

    def get_required_aegis_permission(self, request):
        if request.method == "POST":
            return Permission.Code.ASSIGNMENT_MANAGE
        return Permission.Code.PROGRAM_VIEW

    def get_program(self, program_id, organization_id):
        try:
            return program_queryset_for(self.request.user).get(pk=program_id)
        except Program.DoesNotExist as exc:
            raise NotFound() from exc

    def get(self, request, program_id):
        program = self.get_program(program_id, request.user.organization_id)
        assignments = ContentAssignment.objects.filter(
            organization_id=request.user.organization_id,
            program=program,
        ).select_related("content")
        if user_is_content_consumer_only(request.user):
            assignments = assignments.filter(
                content__in=content_queryset_for(request.user)
            )
        return Response(
            {"data": ContentAssignmentSerializer(assignments, many=True).data}
        )

    def post(self, request, program_id):
        serializer = ContentAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = create_content_assignment(
                program_id=program_id,
                content_id=serializer.validated_data["content_id"],
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except (Program.DoesNotExist, Content.DoesNotExist) as exc:
            raise NotFound() from exc
        return Response(
            {
                "data": {
                    "program_id": str(assignment.program_id),
                    "content_id": str(assignment.content_id),
                }
            },
            status=status.HTTP_201_CREATED,
        )


class ProgramContentAssignmentDeleteView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.ASSIGNMENT_MANAGE
    http_method_names = ["delete", "head", "options"]

    def delete(self, request, program_id, content_id):
        try:
            remove_content_assignment(
                program_id=program_id,
                content_id=content_id,
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except (
            Program.DoesNotExist,
            Content.DoesNotExist,
            ContentAssignment.DoesNotExist,
        ) as exc:
            raise NotFound() from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramAccessGrantListCreateView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.ACCESS_GRANT
    http_method_names = ["post", "head", "options"]

    def post(self, request):
        serializer = ProgramAccessGrantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grant = grant_program_access(
                user_id=serializer.validated_data["user_id"],
                program_id=serializer.validated_data["program_id"],
                organization_id=request.user.organization_id,
                actor=request.user,
                expires_at=serializer.validated_data.get("expires_at"),
            )
        except (User.DoesNotExist, Program.DoesNotExist) as exc:
            raise NotFound() from exc
        return Response(
            {"data": ProgramAccessGrantSerializer(grant).data},
            status=status.HTTP_201_CREATED,
        )


class ProgramAccessGrantRevokeView(APIView):
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    required_aegis_permission = Permission.Code.ACCESS_REVOKE
    http_method_names = ["post", "head", "options"]

    def post(self, request, grant_id):
        try:
            grant = revoke_program_access(
                grant_id=grant_id,
                organization_id=request.user.organization_id,
                actor=request.user,
            )
        except ProgramAccessGrant.DoesNotExist as exc:
            raise NotFound() from exc
        return Response({"data": ProgramAccessGrantSerializer(grant).data})


class UserAccessGrantListView(generics.ListAPIView):
    serializer_class = ProgramAccessGrantSerializer
    permission_classes = [HasAegisPermission]
    authentication_classes = [ApiSessionAuthentication]
    http_method_names = ["get", "head", "options"]

    def get_required_aegis_permission(self, request):
        if str(self.kwargs["user_id"]) == str(request.user.id):
            return Permission.Code.PROFILE_VIEW_OWN
        return Permission.Code.ACCESS_GRANT

    def get_queryset(self):
        return ProgramAccessGrant.objects.filter(
            organization_id=self.request.user.organization_id,
            user_id=self.kwargs["user_id"],
        ).select_related("program", "user", "granted_by", "revoked_by")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response
