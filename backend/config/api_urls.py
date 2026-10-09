"""API v1 URL namespace."""

from django.urls import include, path


urlpatterns = [
	path("", include("identity.urls")),
	path("", include("knowledge.urls")),
]
