"""Routage racine de l'API FIN_FLOW."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.accounts.auth_views import (
    LogoutView,
    MfaConfirmView,
    MfaDisableView,
    MfaSetupView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)
from apps.common.health import HealthView, MetricsView

api_v1 = [
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="token_logout"),
    path("auth/mfa/setup/", MfaSetupView.as_view(), name="mfa_setup"),
    path("auth/mfa/confirm/", MfaConfirmView.as_view(), name="mfa_confirm"),
    path("auth/mfa/disable/", MfaDisableView.as_view(), name="mfa_disable"),
    path("health/", HealthView.as_view(), name="health"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("", include("apps.tenants.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.credits.urls")),
    path("", include("apps.workflow.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.guarantees.urls")),
    path("", include("apps.sureties.urls")),
    path("", include("apps.contracts.urls")),
    path("", include("apps.corebanking.urls")),
    path("", include("apps.collections.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.reporting.urls")),
    path("", include("apps.notifications.urls")),
]

urlpatterns = [
    # Hors du préfixe /admin/ réservé à la SPA React (sinon F5 → admin Django).
    path("django-admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    *([
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ] if getattr(settings, "STORAGE_BACKEND", "local") != "s3" else []),
]

if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass
