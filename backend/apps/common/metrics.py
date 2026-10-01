"""Métriques Prometheus : HTTP (compteurs) et sondes live (base, Celery, CBS)."""
from __future__ import annotations

import logging
import os
from datetime import timedelta

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

logger = logging.getLogger("finflow.metrics")

HTTP_REQUESTS = Counter(
    "finflow_http_requests_total",
    "Nombre de requêtes HTTP",
    ["method", "status", "route"],
)
HTTP_LATENCY = Histogram(
    "finflow_http_request_duration_seconds",
    "Durée des requêtes HTTP",
    ["method", "route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 1.5, 2.5, 5, 10),
)


def observe_http(request, response, elapsed_s: float) -> None:
    try:
        route = _route_label(request)
        method = getattr(request, "method", "GET") or "GET"
        status = str(getattr(response, "status_code", 0))
        HTTP_REQUESTS.labels(method, status, route).inc()
        HTTP_LATENCY.labels(method, route).observe(max(elapsed_s, 0))
    except Exception:  # noqa: BLE001
        logger.debug("observe_http ignoré", exc_info=True)


def _route_label(request) -> str:
    match = getattr(request, "resolver_match", None)
    route = getattr(match, "route", None) if match else None
    if route:
        return str(route)[:120]
    path = getattr(request, "path", "") or "/"
    parts = []
    for part in path.strip("/").split("/"):
        if not part:
            continue
        if part.isdigit() or (len(part) >= 32 and "-" in part):
            parts.append(":id")
        else:
            parts.append(part[:40])
        if len(parts) >= 6:
            break
    return "/" + "/".join(parts) if parts else "/"


class _LiveCollector:
    """Sondes recalculées à chaque scrape (état global, pas par worker)."""

    def collect(self):
        from apps.common.health import _check_cache, _check_database, _check_storage

        for name, result in (
            ("database", _check_database()),
            ("cache", _check_cache()),
            ("storage", _check_storage()),
        ):
            gauge = GaugeMetricFamily(
                f"finflow_health_{name}",
                f"1 si le contrôle {name} réussit",
            )
            gauge.add_metric([], 1 if result.get("ok") else 0)
            yield gauge
            if "latency_ms" in result:
                latency = GaugeMetricFamily(
                    f"finflow_health_{name}_latency_seconds",
                    f"Latence du contrôle {name}",
                )
                latency.add_metric([], float(result["latency_ms"]) / 1000.0)
                yield latency

        length, broker_up = _celery_queue()
        broker = GaugeMetricFamily(
            "finflow_celery_broker_up",
            "1 si le broker Redis répond",
        )
        broker.add_metric([], 1 if broker_up else 0)
        yield broker
        queue = GaugeMetricFamily(
            "finflow_celery_queue_length",
            "Messages en attente sur la file celery",
        )
        queue.add_metric([], length)
        yield queue

        cbs = _cbs_counts()
        for key, help_text in (
            ("failed_recent", "Journaux CBS FAILED sur les 15 dernières minutes"),
            ("retry", "Journaux CBS au statut RETRY"),
            ("outbox_failed", "Événements outbox CBS FAILED"),
            ("outbox_orphan", "Événements outbox CBS ORPHAN"),
            ("outbox_pending", "Événements outbox CBS PENDING"),
        ):
            family = GaugeMetricFamily(f"finflow_cbs_{key}", help_text)
            family.add_metric([], cbs[key])
            yield family

        used, quota, ratio = _ged_usage()
        for metric_name, help_text, value in (
            ("finflow_ged_used_bytes", "Octets GED utilisés, toutes filiales", used),
            ("finflow_ged_quota_bytes", "Quota GED total, toutes filiales", quota),
            ("finflow_ged_quota_ratio", "Usage GED / quota (0 si quota nul)", ratio),
        ):
            family = GaugeMetricFamily(metric_name, help_text)
            family.add_metric([], value)
            yield family


def _celery_queue() -> tuple[float, bool]:
    try:
        from django.conf import settings
        import redis

        url = getattr(settings, "CELERY_BROKER_URL", "") or ""
        if not url.startswith("redis"):
            return 0, False
        client = redis.Redis.from_url(
            url, socket_connect_timeout=0.4, socket_timeout=0.4
        )
        up = bool(client.ping())
        return float(client.llen("celery") or 0), up
    except Exception:  # noqa: BLE001
        return 0, False


def _cbs_counts() -> dict[str, float]:
    empty = {
        "failed_recent": 0,
        "retry": 0,
        "outbox_failed": 0,
        "outbox_orphan": 0,
        "outbox_pending": 0,
    }
    try:
        from django.utils import timezone

        from apps.corebanking.models import IntegrationLog
        from apps.corebanking.outbox import CbsOutboxEvent

        since = timezone.now() - timedelta(minutes=15)
        empty["failed_recent"] = IntegrationLog.all_tenants.filter(
            status=IntegrationLog.Status.FAILED,
            updated_at__gte=since,
        ).count()
        empty["retry"] = IntegrationLog.all_tenants.filter(
            status=IntegrationLog.Status.RETRY,
        ).count()
        empty["outbox_failed"] = CbsOutboxEvent.all_tenants.filter(
            status=CbsOutboxEvent.Status.FAILED,
        ).count()
        empty["outbox_orphan"] = CbsOutboxEvent.all_tenants.filter(
            status=CbsOutboxEvent.Status.ORPHAN,
        ).count()
        empty["outbox_pending"] = CbsOutboxEvent.all_tenants.filter(
            status=CbsOutboxEvent.Status.PENDING,
        ).count()
    except Exception:  # noqa: BLE001
        logger.debug("compteurs CBS indisponibles", exc_info=True)
    return empty


def _ged_usage() -> tuple[float, float, float]:
    try:
        from apps.tenants.models import Tenant

        used = quota = 0
        for row_used, row_quota in Tenant.objects.values_list(
            "ged_used_bytes", "ged_quota_bytes"
        ):
            used += int(row_used or 0)
            quota += int(row_quota or 0)
        ratio = (used / quota) if quota else 0.0
        return float(used), float(quota), float(ratio)
    except Exception:  # noqa: BLE001
        logger.debug("compteurs GED indisponibles", exc_info=True)
        return 0.0, 0.0, 0.0


_live_hooked = False


def render_metrics() -> tuple[bytes, str]:
    global _live_hooked
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        registry.register(_LiveCollector())
        return generate_latest(registry), CONTENT_TYPE_LATEST
    if not _live_hooked:
        REGISTRY.register(_LiveCollector())
        _live_hooked = True
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
