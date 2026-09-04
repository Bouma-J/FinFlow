"""Vues callback CBS (webhooks Perfect)."""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.corebanking.disbursement import apply_cbs_callback
from apps.corebanking.services import CoreBankingError


class CreditDisbursementCallbackView(APIView):
    """
    Callback Perfect pour une demande de crédit / décaissement.

    POST /api/v1/cbs/callbacks/crd/<application_id>/
    Header optionnel : X-CBS-Callback-Secret (si configuré sur le connecteur).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, application_id):
        secret = (
            request.headers.get("X-CBS-Callback-Secret")
            or request.query_params.get("secret")
            or ""
        ).strip() or None
        try:
            result = apply_cbs_callback(
                application_id, request.data, secret=secret
            )
        except CoreBankingError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"detail": "Callback enregistré.", **result})
