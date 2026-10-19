from django.urls import path

from .views import (
    ActivityEventListView,
    AuditRecordListView,
    RiskInvestigationDetailView,
    RiskInvestigationListCreateView,
    RiskSignalListView,
    RiskSignalSummaryView,
    SecurityEventListView,
)


urlpatterns = [
    path("activities/", ActivityEventListView.as_view(), name="activity-list"),
    path("audits/", AuditRecordListView.as_view(), name="audit-list"),
    path(
        "security-events/",
        SecurityEventListView.as_view(),
        name="security-event-list",
    ),
    path("risk-signals/", RiskSignalListView.as_view(), name="risk-signal-list"),
    path(
        "risk-signals/summary/",
        RiskSignalSummaryView.as_view(),
        name="risk-signal-summary",
    ),
    path(
        "risk-investigations/",
        RiskInvestigationListCreateView.as_view(),
        name="risk-investigation-list",
    ),
    path(
        "risk-investigations/<uuid:investigation_id>/",
        RiskInvestigationDetailView.as_view(),
        name="risk-investigation-detail",
    ),
]
