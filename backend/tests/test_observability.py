"""Exposition Prometheus et remontée des erreurs d'écran."""
import logging

import pytest
from django.test import Client, override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_prometheus_metrics_expose_health():
    response = Client().get("/metrics")
    assert response.status_code == 200
    body = response.content.decode()
    assert "finflow_health_database" in body
    assert "finflow_celery_broker_up" in body
    assert "finflow_cbs_failed_recent" in body
    assert "finflow_ged_quota_ratio" in body


@override_settings(PROMETHEUS_METRICS_TOKEN="jeton-test")
def test_prometheus_metrics_require_token_when_configured():
    client = Client()
    assert client.get("/metrics").status_code == 403
    ok = client.get("/metrics", HTTP_AUTHORIZATION="Bearer jeton-test")
    assert ok.status_code == 200


@pytest.mark.django_db
def test_client_error_is_logged(caplog):
    response = APIClient().post(
        "/api/v1/client-errors/",
        {"message": "ecran casse", "path": "/clients", "stack": "Error: ecran"},
        format="json",
    )
    assert response.status_code == 204
    assert any("client_error" in rec.message and "ecran casse" in rec.message for rec in caplog.records)


def test_client_error_rejects_empty_message():
    response = APIClient().post("/api/v1/client-errors/", {"message": "  "}, format="json")
    assert response.status_code == 400


@override_settings(ALERT_WEBHOOK_TOKEN="jeton-alerte", ALERT_EMAIL_TO="")
def test_alert_webhook_logs_firing_alert(caplog):
    log = logging.getLogger("finflow")
    log.addHandler(caplog.handler)
    try:
        response = APIClient().post(
            "/api/v1/alert-webhook/",
            {
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "FinflowDatabaseDown", "severity": "critical"},
                        "annotations": {"summary": "La base ne répond plus"},
                    }
                ],
            },
            format="json",
            HTTP_AUTHORIZATION="Bearer jeton-alerte",
        )
        assert response.status_code == 204
        assert any("FinflowDatabaseDown" in rec.message for rec in caplog.records)
    finally:
        log.removeHandler(caplog.handler)


@override_settings(ALERT_WEBHOOK_TOKEN="jeton-alerte")
def test_alert_webhook_rejects_missing_token():
    response = APIClient().post("/api/v1/alert-webhook/", {"alerts": []}, format="json")
    assert response.status_code == 403


@override_settings(ALERT_WEBHOOK_TOKEN="", DEBUG=False)
def test_alert_webhook_hidden_without_token_outside_debug():
    response = APIClient().post("/api/v1/alert-webhook/", {"alerts": []}, format="json")
    assert response.status_code == 404
