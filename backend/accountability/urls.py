from django.urls import path

from .views import ActivityEventListView, AuditRecordListView, SecurityEventListView


urlpatterns = [
    path("activities/", ActivityEventListView.as_view(), name="activity-list"),
    path("audits/", AuditRecordListView.as_view(), name="audit-list"),
    path(
        "security-events/",
        SecurityEventListView.as_view(),
        name="security-event-list",
    ),
]
