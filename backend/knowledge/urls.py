from django.urls import path

from .views import (
    ContentArchiveView,
    ContentDetailView,
    ContentListCreateView,
    ContentVersionDetailView,
    ContentVersionListView,
    ContentVersionArchiveView,
    ContentVersionPublishView,
)


urlpatterns = [
    path("content/", ContentListCreateView.as_view(), name="content-list"),
    path(
        "content/<uuid:pk>/",
        ContentDetailView.as_view(),
        name="content-detail",
    ),
    path(
        "content/<uuid:pk>/archive/",
        ContentArchiveView.as_view(),
        name="content-archive",
    ),
    path(
        "content/<uuid:content_id>/versions/",
        ContentVersionListView.as_view(),
        name="content-version-list",
    ),
    path(
        "content/<uuid:content_id>/versions/<uuid:pk>/",
        ContentVersionDetailView.as_view(),
        name="content-version-detail",
    ),
    path(
        "content/<uuid:content_id>/versions/<uuid:version_id>/publish/",
        ContentVersionPublishView.as_view(),
        name="content-version-publish",
    ),
    path(
        "content/<uuid:content_id>/versions/<uuid:version_id>/archive/",
        ContentVersionArchiveView.as_view(),
        name="content-version-archive",
    ),
]
