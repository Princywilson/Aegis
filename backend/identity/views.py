from django.db import IntegrityError, transaction
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accountability.models import AuditRecord, SecurityEvent
from accountability.services import (
    is_login_rate_limited,
    record_login_failure,
    record_login_success,
    record_logout,
)

from .models import Organization, User
from .models import Permission, Role
from .permissions import HasAegisPermission, has_permission
from .rbac import effective_permission_codes, effective_role_names
from .serializers import (
    LoginSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSummarySerializer,
    UserUpdateSerializer,
)


def api_error(code, message, status_code, details=None):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
        status=status_code,
    )


def user_summary(user):
    return {
        "id": str(user.id),
        "name": " ".join(
            part for part in (user.first_name, user.last_name) if part
        ),
        "email": user.email,
        "organization": {
            "id": str(user.organization_id),
            "name": user.organization.name,
        },
    }


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"data": {"csrf_token": get_token(request)}})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error(
                "VALIDATION_ERROR",
                "One or more fields are invalid.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        credentials = serializer.validated_data
        source_ip = request.META.get("REMOTE_ADDR", "")
        if is_login_rate_limited(
            credentials["organization_slug"],
            credentials["email"],
            source_ip,
        ):
            return api_error(
                "AUTHENTICATION_FAILED",
                "The supplied credentials are invalid or temporarily unavailable.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(request, **credentials)
        if user is None:
            organization = Organization.objects.filter(
                slug=credentials["organization_slug"]
            ).first()
            event_user = None
            if organization is not None:
                event_user = User.objects.filter(
                    organization=organization,
                    email=User.objects.normalize_email(credentials["email"]),
                ).first()

            rate_limited = record_login_failure(
                credentials["organization_slug"],
                credentials["email"],
                source_ip,
                organization=organization,
                user=event_user,
            )
            return api_error(
                "AUTHENTICATION_FAILED",
                "The supplied credentials are invalid or temporarily unavailable.",
                (
                    status.HTTP_429_TOO_MANY_REQUESTS
                    if rate_limited
                    else status.HTTP_401_UNAUTHORIZED
                ),
            )

        if not record_login_success(
            user.organization,
            user,
            credentials["organization_slug"],
            credentials["email"],
            source_ip,
        ):
            return api_error(
                "AUTHENTICATION_FAILED",
                "The supplied credentials are invalid or temporarily unavailable.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        login(request, user)
        return Response(
            {
                "data": {
                    "user": {
                        "id": str(user.id),
                        "name": " ".join(
                            part for part in (user.first_name, user.last_name) if part
                        ),
                        "organization_id": str(user.organization_id),
                    }
                }
            }
        )


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        if not request.user.is_authenticated:
            return api_error(
                "AUTHENTICATION_FAILED",
                "Authentication is required to complete this request.",
                status.HTTP_401_UNAUTHORIZED,
            )

        record_logout(request.user.organization, request.user)
        logout(request)
        return Response({"data": {"message": "Logout successful."}})


class CurrentUserView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return api_error(
                "AUTHENTICATION_FAILED",
                "Authentication is required to complete this request.",
                status.HTTP_401_UNAUTHORIZED,
            )

        data = user_summary(request.user)
        data["roles"] = effective_role_names(request.user)
        data["permissions"] = effective_permission_codes(request.user)
        return Response({"data": data})


class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        value = request.query_params.get(self.page_size_query_param)
        if value is None:
            return self.page_size
        try:
            page_size = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"page_size": ["A valid integer is required."]}) from exc
        if page_size < 1:
            raise ValidationError({"page_size": ["Must be greater than zero."]})
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


class UserListCreateView(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasAegisPermission]
    pagination_class = UserPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_required_aegis_permission(self, request):
        return (
            Permission.Code.USER_CREATE
            if request.method == "POST"
            else Permission.Code.USER_VIEW
        )

    def get_queryset(self):
        params = self.request.query_params
        allowed = {"page", "page_size", "role", "status", "search"}
        unknown = set(params) - allowed
        if unknown:
            raise ValidationError(
                {key: ["Unexpected query parameter."] for key in sorted(unknown)}
            )
        queryset = User.objects.filter(
            organization_id=self.request.user.organization_id
        ).prefetch_related("user_roles__role")

        role_code = params.get("role")
        if role_code:
            if not Role.objects.filter(
                organization_id=self.request.user.organization_id,
                code=role_code,
            ).exists():
                raise ValidationError({"role": ["Select a valid role."]})
            queryset = queryset.filter(
                user_roles__organization_id=self.request.user.organization_id,
                user_roles__role__organization_id=self.request.user.organization_id,
                user_roles__role__code=role_code,
            )

        status_filter = params.get("status")
        if status_filter:
            status_filter = status_filter.upper()
            if status_filter not in User.Status.values:
                raise ValidationError({"status": ["Select a valid user status."]})
            queryset = queryset.filter(status=status_filter)

        search = params.get("search")
        if search:
            search = search.strip()
            if len(search) > 200:
                raise ValidationError(
                    {"search": ["Ensure this field has no more than 200 characters."]}
                )
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset.distinct().order_by("email", "id")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSummarySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        roles = serializer.validated_data.get("role_ids", [])
        if roles and not has_permission(request.user, Permission.Code.ROLE_MANAGE):
            return api_error(
                "FORBIDDEN",
                "Role management permission is required to assign roles.",
                status.HTTP_403_FORBIDDEN,
            )
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            return api_error(
                "CONFLICT",
                "A user with this email already exists in the organization.",
                status.HTTP_409_CONFLICT,
            )
        data = UserSummarySerializer(user).data
        data["temporary_password"] = user._temporary_password
        return Response({"data": data}, status=status.HTTP_201_CREATED)


class UserDetailView(generics.GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasAegisPermission]
    http_method_names = ["get", "patch", "head", "options"]

    def get_required_aegis_permission(self, request):
        return (
            Permission.Code.USER_UPDATE
            if request.method == "PATCH"
            else Permission.Code.USER_VIEW
        )

    def get_queryset(self):
        return User.objects.filter(
            organization_id=self.request.user.organization_id
        ).prefetch_related("user_roles__role")

    def get_object(self):
        try:
            return self.get_queryset().get(pk=self.kwargs["user_id"])
        except User.DoesNotExist as exc:
            raise NotFound() from exc

    def get(self, request, *args, **kwargs):
        return Response({"data": UserSummarySerializer(self.get_object()).data})

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        if (
            serializer.validated_data.get("status") == "inactive"
            and not has_permission(request.user, Permission.Code.USER_DEACTIVATE)
        ):
            return api_error(
                "FORBIDDEN",
                "User deactivation permission is required.",
                status.HTTP_403_FORBIDDEN,
            )
        user = serializer.save()
        return Response({"data": UserSummarySerializer(user).data})


class RoleListView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasAegisPermission]
    serializer_class = RoleSerializer

    def get_required_aegis_permission(self, request):
        return Permission.Code.ROLE_MANAGE

    def get_queryset(self):
        return Role.objects.filter(
            organization_id=self.request.user.organization_id
        ).order_by("name", "id")

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"data": serializer.data})


class PermissionListView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasAegisPermission]
    serializer_class = PermissionSerializer

    def get_required_aegis_permission(self, request):
        return Permission.Code.ROLE_MANAGE

    def get_queryset(self):
        return Permission.objects.order_by("code")

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"data": serializer.data})