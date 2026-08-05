"""Configuration de production."""
from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, STORAGE_BACKEND, env

DEBUG = False

# Sécurité renforcée
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

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
