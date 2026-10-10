from django.urls import path

from .views import (
    CsrfTokenView,
    CurrentUserView,
    LoginView,
    LogoutView,
    PermissionListView,
    RoleListView,
    UserDetailView,
    UserListCreateView,
)


urlpatterns = [
    path("auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
]