"""Active Sentry dès qu'un DSN est fourni (dev ou production)."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("finflow")


def configure_sentry() -> None:
    dsn = (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError:
        logger.warning("SENTRY_DSN est défini mais le paquet sentry-sdk est absent.")
        return

    try:
        sample = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE") or "0.1")
    except ValueError:
        sample = 0.1

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=sample,
        send_default_pii=False,
        environment=os.environ.get("SENTRY_ENVIRONMENT") or "production",
    )


def capture_client_error(message: str, *, path: str = "", stack: str = "") -> None:
    """Journalise une erreur d'écran et la transmet à Sentry si le DSN est actif."""
    logger.error("client_error path=%s message=%s", path[:200], message[:500])
    if stack:
        logger.error("client_error_stack %s", stack[:4000])
    try:
        import sentry_sdk

        client = sentry_sdk.get_client()
        dsn = getattr(client, "dsn", None)
        if dsn:
            sentry_sdk.capture_message(
                f"{path}: {message}"[:500],
                level="error",
            )
    except Exception:  # noqa: BLE001
        return
