"""Exposition Prometheus, erreurs d'écran et réception des alertes."""
from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.common.metrics import render_metrics
from apps.common.sentry_setup import capture_client_error

logger = logging.getLogger("finflow")


class PrometheusMetricsView(APIView):
    """Texte Prometheus sur GET /metrics.

    Si ``PROMETHEUS_METRICS_TOKEN`` est défini, l'appelant doit envoyer
    ``Authorization: Bearer <jeton>``.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        expected = (getattr(settings, "PROMETHEUS_METRICS_TOKEN", "") or "").strip()
        if expected:
            header = request.META.get("HTTP_AUTHORIZATION", "")
            if header != f"Bearer {expected}":
                return HttpResponse(status=403)
        body, content_type = render_metrics()
        return HttpResponse(body, content_type=content_type)


class ClientErrorThrottle(AnonRateThrottle):
    scope = "client_error"


class ClientErrorView(APIView):
    """Reçoit les exceptions React (message court, pas de données métier)."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ClientErrorThrottle]

    def post(self, request):
        message = str(request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "message requis"}, status=400)
        path = str(request.data.get("path") or "")[:200]
        stack = str(request.data.get("stack") or "")[:4000]
        capture_client_error(message[:500], path=path, stack=stack)
        return Response(status=204)


class AlertWebhookView(APIView):
    """Reçoit les alertes Alertmanager, les journalise, et envoie un e-mail si configuré."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        expected = (getattr(settings, "ALERT_WEBHOOK_TOKEN", "") or "").strip()
        if not expected:
            if not settings.DEBUG:
                return HttpResponse(status=404)
        else:
            header = request.META.get("HTTP_AUTHORIZATION", "")
            if header != f"Bearer {expected}":
                return HttpResponse(status=403)

        alerts = request.data.get("alerts") if isinstance(request.data, dict) else None
        if not isinstance(alerts, list):
            alerts = []
        lines = [_format_alert(item) for item in alerts if isinstance(item, dict)]
        lines = [line for line in lines if line]
        if not lines:
            return Response(status=204)

        status = str(request.data.get("status") or "firing")
        logger.error("alert_webhook status=%s count=%s\n%s", status, len(lines), "\n".join(lines))
        _email_alerts(status, lines)
        return Response(status=204)


def _format_alert(item: dict) -> str:
    labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
    annotations = item.get("annotations") if isinstance(item.get("annotations"), dict) else {}
    name = str(labels.get("alertname") or "alerte")[:80]
    severity = str(labels.get("severity") or "")[:20]
    summary = str(annotations.get("summary") or "")[:300]
    state = str(item.get("status") or "")[:20]
    return f"{state} {severity} {name}: {summary}".strip()


def _email_alerts(status: str, lines: list[str]) -> None:
    recipient = (getattr(settings, "ALERT_EMAIL_TO", "") or "").strip()
    if not recipient:
        return
    try:
        from django.core.mail import send_mail

        send_mail(
            subject=f"FIN_FLOW {status}: {len(lines)} alerte(s)",
            message="\n".join(lines),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[part.strip() for part in recipient.split(",") if part.strip()],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception("envoi e-mail d'alerte impossible")
