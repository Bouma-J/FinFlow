"""Configuration de production."""
from apps.common.https import host_is_ipv4

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, STORAGE_BACKEND, env

DEBUG = False

# Docs API désactivées par défaut en production
ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=False)

# Sécurité renforcée
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

# HSTS : 1 an + preload sur un nom de domaine. Sur une IP, un max-age long
# (surtout preload) verrouille les navigateurs si le certificat expire
# (Let's Encrypt IP = ~6 jours). Surcharge via DJANGO_SECURE_HSTS_*.
def _opt_bool(key: str, default: bool) -> bool:
    raw = (env(key, default="") or "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "on"}


_hsts_raw = (env("DJANGO_SECURE_HSTS_SECONDS", default="") or "").strip()
_frontend_url = env("FRONTEND_BASE_URL", default="")
if _hsts_raw == "" and host_is_ipv4(_frontend_url):
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SECURE_HSTS_SECONDS = int(_hsts_raw) if _hsts_raw != "" else 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _opt_bool(
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True
    )
    SECURE_HSTS_PRELOAD = _opt_bool("DJANGO_SECURE_HSTS_PRELOAD", True)

_csrf = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
if not _csrf:
    if _frontend_url:
        _csrf.append(_frontend_url.rstrip("/"))
    for _origin in CORS_ALLOWED_ORIGINS:  # noqa: F405
        if _origin not in _csrf:
            _csrf.append(_origin)
CSRF_TRUSTED_ORIGINS = _csrf

# Fichiers statiques servis par WhiteNoise
MIDDLEWARE = MIDDLEWARE[:1] + [
    "whitenoise.middleware.WhiteNoiseMiddleware"
] + MIDDLEWARE[1:]

_staticfiles = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}

if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": STORAGES["default"],  # noqa: F405
        "staticfiles": _staticfiles,
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": _staticfiles,
    }

# Supervision des erreurs (optionnel)
SENTRY_DSN = env("SENTRY_DSN", default="")

# A1 — jamais démarrer en prod avec une clé faible / connue
_INSECURE_SECRETS = frozenset(
    {
        "insecure-dev-key-change-me",
        "change-me-in-production",
        "changeme",
        "secret",
        "django-insecure",
        # Clés démo Compose (versionnées dans le repo)
        "finflow-local-compose-demo-key-not-for-production-use-x9K2mP7qR4",
        "finflow-local",
        # Clé Fernet test (présente dans test.py et Compose)
        "jyYZdpd3kTY2RiW3UUFhbGMQuJCrQIFjO1ed6zowfqk=",
    }
)
_sk = SECRET_KEY or ""  # noqa: F405
if (
    not _sk
    or _sk in _INSECURE_SECRETS
    or len(_sk) < 40
    or "change-me" in _sk.lower()
    or "insecure" in _sk.lower()
):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être une valeur forte (≥ 40 caractères) en "
        "production. Les valeurs connues (change-me-in-production, "
        "insecure-dev-key-change-me, etc.) sont refusées."
    )

# Coffre secrets applicatifs (SMTP / CBS) — indépendant de SECRET_KEY
_field_key = (FIELD_ENCRYPTION_KEY or "").strip()  # noqa: F405
if not _field_key:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "FIELD_ENCRYPTION_KEY est obligatoire en production "
        "(Fernet url-safe, indépendant de DJANGO_SECRET_KEY)."
    )

# Refuser clés Fernet de test/démo connues
_INSECURE_FERNET_KEYS = frozenset(
    {
        "jyYZdpd3kTY2RiW3UUFhbGMQuJCrQIFjO1ed6zowfqk=",  # test.py + Compose
        "test-key",
        "demo-key",
    }
)
if _field_key in _INSECURE_FERNET_KEYS:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        f"FIELD_ENCRYPTION_KEY ne peut pas être une clé de test connue. "
        f"Générez une nouvelle clé Fernet avec: "
        f"python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

# Redis auth obligatoire en production
# Format attendu: redis://:password@host:port/db ou rediss://...
_broker = CELERY_BROKER_URL  # noqa: F405
_result = CELERY_RESULT_BACKEND  # noqa: F405
_cache = env("REDIS_CACHE_URL", default="")

def _redis_has_auth(url: str) -> bool:
    """Vérifie qu'une URL Redis contient un mot de passe."""
    if not url or "redis" not in url:
        return True  # Pas Redis
    # Format: redis://:password@host ou redis://user:password@host
    if "://:@" in url or "://localhost" in url or url.count(":") < 3:
        return False  # Pas de password
    # Vérifier présence password après ://
    if "://" in url:
        after_scheme = url.split("://", 1)[1]
        if "@" not in after_scheme:
            return False  # Pas de credentials
        creds = after_scheme.split("@", 1)[0]
        if not creds or creds == ":":
            return False  # Credentials vides
    return True

if not _redis_has_auth(_broker) or not _redis_has_auth(_result) or (_cache and not _redis_has_auth(_cache)):
    from django.core.exceptions import ImproperlyConfigured
    
    raise ImproperlyConfigured(
        "Redis DOIT avoir un mot de passe en production. "
        "Format attendu: redis://:PASSWORD@host:port/db\n"
        "Vérifiez: CELERY_BROKER_URL, CELERY_RESULT_BACKEND, REDIS_CACHE_URL"
    )

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", default="0.1")),
        send_default_pii=False,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
    )
