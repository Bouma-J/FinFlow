"""
Système de monitoring et observabilité centralisé.

Intègre:
- Sentry pour le tracking des erreurs
- Métriques Prometheus
- Logs structurés
"""
import logging
import time
from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from rest_framework import status

logger = logging.getLogger("finflow.monitoring")

# ============================================================================
# Métriques et compteurs
# ============================================================================

class Metrics:
    """
    Système de métriques simple en mémoire.
    Pour production avancée, utiliser Prometheus ou DataDog.
    """
    
    _counters: dict[str, int] = {}
    _gauges: dict[str, float] = {}
    _timers: dict[str, list[float]] = {}
    
    @classmethod
    def increment(cls, name: str, value: int = 1):
        """Incrémenter un compteur."""
        cls._counters[name] = cls._counters.get(name, 0) + value
    
    @classmethod
    def gauge(cls, name: str, value: float):
        """Enregistrer une valeur de gauge."""
        cls._gauges[name] = value
    
    @classmethod
    def timing(cls, name: str, duration_ms: float):
        """Enregistrer une durée."""
        if name not in cls._timers:
            cls._timers[name] = []
        cls._timers[name].append(duration_ms)
        # Garder seulement les 1000 dernières mesures
        if len(cls._timers[name]) > 1000:
            cls._timers[name] = cls._timers[name][-1000:]
    
    @classmethod
    def get_all(cls) -> dict[str, Any]:
        """Récupérer toutes les métriques."""
        timers_stats = {}
        for name, values in cls._timers.items():
            if values:
                timers_stats[name] = {
                    "count": len(values),
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values),
                }
        
        return {
            "counters": cls._counters.copy(),
            "gauges": cls._gauges.copy(),
            "timers": timers_stats,
        }
    
    @classmethod
    def reset(cls):
        """Réinitialiser toutes les métriques."""
        cls._counters.clear()
        cls._gauges.clear()
        cls._timers.clear()


def track_time(metric_name: str):
    """Décorateur pour tracker le temps d'exécution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                Metrics.timing(metric_name, duration_ms)
        return wrapper
    return decorator


# ============================================================================
# Health Checks Détaillés
# ============================================================================

def check_database() -> tuple[bool, str, dict]:
    """Vérifier la connexion à la base de données."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok", {"type": settings.DATABASES["default"]["ENGINE"]}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, "error", {"error": str(e)}


def check_cache() -> tuple[bool, str, dict]:
    """Vérifier le cache Redis."""
    try:
        test_key = "__health_check__"
        test_value = "test"
        cache.set(test_key, test_value, timeout=10)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved == test_value:
            return True, "ok", {"backend": settings.CACHES["default"]["BACKEND"]}
        return False, "error", {"error": "Cache value mismatch"}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False, "error", {"error": str(e)}


def check_storage() -> tuple[bool, str, dict]:
    """Vérifier le stockage S3/MinIO."""
    try:
        from apps.documents.storage import default_storage
        
        # Vérifier que le bucket existe et est accessible
        exists = default_storage.bucket_exists()
        if exists:
            return True, "ok", {
                "backend": getattr(settings, "STORAGE_BACKEND", "local"),
                "bucket": getattr(settings, "AWS_STORAGE_BUCKET_NAME", "local"),
            }
        return False, "error", {"error": "Bucket not accessible"}
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False, "degraded", {"error": str(e)}


def check_celery() -> tuple[bool, str, dict]:
    """Vérifier que Celery est opérationnel."""
    try:
        from celery import current_app
        
        # Vérifier la connexion au broker
        with current_app.connection_or_acquire() as conn:
            conn.default_channel.queue_declare(
                queue="health_check_queue",
                passive=True,
            )
        
        return True, "ok", {"broker": settings.CELERY_BROKER_URL.split("@")[0]}
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        return False, "degraded", {"error": str(e)}


def get_system_health() -> dict:
    """Obtenir un rapport complet de santé du système."""
    checks = {
        "database": check_database(),
        "cache": check_cache(),
        "storage": check_storage(),
        "celery": check_celery(),
    }
    
    overall_healthy = all(healthy for healthy, _, _ in checks.values())
    degraded = any(
        status_str == "degraded" for _, status_str, _ in checks.values()
    )
    
    if overall_healthy:
        overall_status = "healthy"
    elif degraded or any(healthy for healthy, _, _ in checks.values()):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "ready": overall_healthy or degraded,
        "checks": {
            name: {
                "healthy": healthy,
                "status": status_str,
                "details": details,
            }
            for name, (healthy, status_str, details) in checks.items()
        },
        "version": getattr(settings, "APP_VERSION", "dev"),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
    }


# ============================================================================
# Vue Health Check pour l'API
# ============================================================================

def health_check_view(request):
    """
    Endpoint de health check pour monitoring externe.
    
    GET /api/v1/health/
    
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


# ============================================================================
# Intégration Sentry
# ============================================================================

def init_sentry():
    """Initialiser Sentry pour le tracking des erreurs."""
    sentry_dsn = getattr(settings, "SENTRY_DSN", None)
    
    if not sentry_dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            environment=getattr(settings, "ENVIRONMENT", "development"),
            release=getattr(settings, "APP_VERSION", None),
            traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1),
            profiles_sample_rate=getattr(settings, "SENTRY_PROFILES_SAMPLE_RATE", 0.1),
            send_default_pii=False,  # Ne pas envoyer de données personnelles
            before_send=before_send_sentry_event,
        )
        
        logger.info("Sentry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_sentry_event(event, hint):
    """
    Filtrer/modifier les événements avant envoi à Sentry.
    Supprimer les données sensibles.
    """
    # Supprimer les mots de passe des données
    if "request" in event:
        if "data" in event["request"]:
            data = event["request"]["data"]
            if isinstance(data, dict):
                for key in ["password", "token", "secret", "api_key"]:
                    if key in data:
                        data[key] = "[FILTERED]"
    
    return event


# ============================================================================
# Logging Structuré
# ============================================================================

class StructuredLogger:
    """Logger avec support de logs structurés (JSON)."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(
        self,
        level: str,
        message: str,
        **context,
    ):
        """Logger un événement avec contexte structuré."""
        log_data = {
            "message": message,
            **context,
        }
        
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra={"context": log_data})
    
    def info(self, message: str, **context):
        self.log_event("INFO", message, **context)
    
    def warning(self, message: str, **context):
        self.log_event("WARNING", message, **context)
    
    def error(self, message: str, **context):
        self.log_event("ERROR", message, **context)
    
    def critical(self, message: str, **context):
        self.log_event("CRITICAL", message, **context)


# Initialiser Sentry au démarrage si configuré
if getattr(settings, "SENTRY_ENABLED", False):
    init_sentry()
