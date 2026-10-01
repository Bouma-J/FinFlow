"""Vues communes à toute l'application."""
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .monitoring import get_system_health, Metrics


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint pour monitoring.
    
    GET /api/v1/health/
    GET /api/v1/health/?metrics=1  (inclure les métriques)
    
    Retourne:
    - 200 si tout est OK
    - 503 si un composant critique est down
    """
    health = get_system_health()
    
    # Ajouter les métriques si demandées
    if request.GET.get("metrics") == "1":
        health["metrics"] = Metrics.get_all()
    
    status_code = (
        status.HTTP_200_OK
        if health["ready"]
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return JsonResponse(health, status=status_code)


@api_view(["GET"])
@permission_classes([AllowAny])
def version_info(request):
    """
    Informations sur la version de l'application.
    
    GET /api/v1/version/
    """
    return JsonResponse({
        "version": getattr(settings, "APP_VERSION", "dev"),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "debug": settings.DEBUG,
    })


@api_view(["GET"])
def metrics_view(request):
    """
    Métriques de l'application (nécessite authentification).
    
    GET /api/v1/metrics/
    """
    return JsonResponse(Metrics.get_all())
