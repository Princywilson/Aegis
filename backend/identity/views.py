from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accountability.models import SecurityEvent
from accountability.services import (
    is_login_rate_limited,
    record_login_failure,
    record_login_success,
    record_logout,
)

from .models import Organization, User
from .rbac import effective_permission_codes, effective_role_names
from .serializers import LoginSerializer


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