from django.urls import path

from .views import (
    GroupBreakdownView,
    GroupConsolidationView,
    OperationalDashboardView,
)

urlpatterns = [
    path("reporting/dashboard/", OperationalDashboardView.as_view(), name="dashboard"),
    path(
        "reporting/group-consolidation/",
        GroupConsolidationView.as_view(),
        name="group-consolidation",
    ),
    path(
        "reporting/group-breakdown/",
        GroupBreakdownView.as_view(),
        name="group-breakdown",
    ),
]
