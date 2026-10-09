from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from identity.models import Permission
from identity.permissions import HasAegisPermission

from .authentication import ApiSessionAuthentication
from .models import Content, ContentVersion
from .serializers import (
    ContentSerializer,
    ContentVersionCreateSerializer,
    ContentVersionSerializer,
)
from .services import (
    archive_content,
    archive_content_version,
    create_content_version,
    publish_content_version,
)


def content_queryset_for(user):
    queryset = Content.objects.filter(organization_id=user.organization_id)
    role_codes = set(user.user_roles.values_list("role__code", flat=True))
    if (
        "content_consumer" in role_codes
        and not role_codes.intersection(
            {"administrator", "content_manager", "management"}
        )
    ):
        return queryset.none()
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
                    "page_size": self.page_size,
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
            raise ValidationError(
                {"program_id": ["Program filtering is available with M6 assignments."]}
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
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

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
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
        return ContentVersion.objects.filter(
            organization_id=self.request.user.organization_id,
            content_id=self.kwargs["content_id"],
        )

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
        return ContentVersion.objects.filter(
            organization_id=self.request.user.organization_id,
            content_id=self.kwargs["content_id"],
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"data": response.data}
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
