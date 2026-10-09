from django.urls import path

from .views import ContentArchiveView, ContentDetailView, ContentListCreateView


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
]
