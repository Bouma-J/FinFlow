"""ViewSets pour l'historique client et la comparaison d'analyses financières."""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import MustChangePasswordGate
from apps.common.tenancy import get_current_tenant_id

logger = logging.getLogger("finflow.credits")


class ClientRenewalViewSet(viewsets.ViewSet):
    """ViewSet pour les fonctionnalités de renouvellement de crédit client."""

    permission_classes = [IsAuthenticated, MustChangePasswordGate]

    @action(detail=True, methods=["get"], url_path="renewal-eligibility")
    def renewal_eligibility(self, request, pk=None):
        """Vérifie l'éligibilité d'un client au renouvellement de crédit.
        
        Retourne :
        - eligible : bool
        - alerts : liste des alertes (bloquantes ou non)
        - repayment_rate : taux de remboursement global
        - history_summary : résumé de l'historique
        """
        from apps.credits.client_history import ClientHistoryService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "Tenant requis"})

        service = ClientHistoryService(client_id=int(pk), tenant_id=tenant_id)

        try:
            eligibility = service.check_renewal_eligibility()
            history = service.get_credit_history()

            return Response(
                {
                    "eligibility": eligibility,
                    "history": history,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(
                f"Erreur vérification éligibilité client {pk}: {e}",
                exc_info=True,
            )
            raise ValidationError({"detail": str(e)}) from e

    @action(detail=True, methods=["get"], url_path="credit-history")
    def credit_history(self, request, pk=None):
        """Récupère l'historique complet des crédits d'un client.
        
        Retourne :
        - total_applications : nombre total de dossiers
        - total_disbursed : nombre de crédits décaissés
        - active_loans_count : nombre de crédits actifs
        - total_borrowed : montant total emprunté
        - total_repaid : montant total remboursé
        - repayment_rate : taux de remboursement (%)
        - has_litigation, has_dation, has_restructuring, has_writeoff : bool
        - loans : liste détaillée des prêts
        """
        from apps.credits.client_history import ClientHistoryService

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "Tenant requis"})

        service = ClientHistoryService(client_id=int(pk), tenant_id=tenant_id)

        try:
            history = service.get_credit_history()
            return Response(history, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Erreur récupération historique client {pk}: {e}",
                exc_info=True,
            )
            raise ValidationError({"detail": str(e)}) from e


class CreditApplicationComparisonViewSet(viewsets.ViewSet):
    """ViewSet pour la comparaison détaillée des analyses financières."""

    permission_classes = [IsAuthenticated, MustChangePasswordGate]

    @action(detail=True, methods=["get"], url_path="financial-comparison")
    def financial_comparison(self, request, pk=None):
        """Retourne une comparaison détaillée de l'analyse financière du dossier
        avec les analyses des crédits antérieurs du même client.
        
        Retourne :
        - previous_analyses : liste des analyses antérieures
        - current_analysis : analyse du dossier actuel
        - income_comparison : comparaison détaillée des revenus
        - expenses_comparison : comparaison détaillée des charges
        - exploitation_comparison : compte d'exploitation (entreprise)
        - balance_comparison : bilan simplifié (entreprise)
        - ratios_comparison : ratios clés (capacité, endettement, DSCR, etc.)
        - score_comparison : évolution du score et recommandation
        - key_insights : insights automatiques sur les changements
        - recommendation_summary : résumé et recommandation
        """
        from apps.credits.financial_comparison import FinancialAnalysisComparison
        from apps.credits.models import CreditApplication

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "Tenant requis"})

        # Récupérer le dossier
        try:
            application = CreditApplication.objects.get(
                pk=int(pk),
                tenant_id=tenant_id,
            )
        except CreditApplication.DoesNotExist:
            raise ValidationError({"detail": "Dossier non trouvé"})

        # Créer le service de comparaison
        service = FinancialAnalysisComparison(
            client_id=application.client_id,
            current_application_id=application.id,
            tenant_id=tenant_id,
        )

        try:
            comparison = service.get_complete_comparison()
            return Response(comparison, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Erreur comparaison analyses dossier {pk}: {e}",
                exc_info=True,
            )
            raise ValidationError({"detail": str(e)}) from e

    @action(detail=True, methods=["get"], url_path="comparison-summary")
    def comparison_summary(self, request, pk=None):
        """Retourne un résumé rapide de la comparaison (pour affichage widget).
        
        Retourne :
        - has_history : bool
        - previous_credits_count : nombre de crédits antérieurs
        - repayment_rate : taux de remboursement global
        - score_trend : INCREASE/DECREASE/STABLE
        - recommendation : recommandation basée sur l'historique
        - main_alerts : liste des 3 alertes principales
        """
        from apps.credits.client_history import ClientHistoryService
        from apps.credits.financial_comparison import FinancialAnalysisComparison
        from apps.credits.models import CreditApplication

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "Tenant requis"})

        # Récupérer le dossier
        try:
            application = CreditApplication.objects.get(
                pk=int(pk),
                tenant_id=tenant_id,
            )
        except CreditApplication.DoesNotExist:
            raise ValidationError({"detail": "Dossier non trouvé"})

        # Service d'historique
        history_service = ClientHistoryService(
            client_id=application.client_id,
            tenant_id=tenant_id,
        )
        history = history_service.get_credit_history()
        eligibility = history_service.check_renewal_eligibility()

        # Service de comparaison
        comparison_service = FinancialAnalysisComparison(
            client_id=application.client_id,
            current_application_id=application.id,
            tenant_id=tenant_id,
        )

        try:
            comparison = comparison_service.get_complete_comparison()
            recommendation_summary = comparison.get("recommendation_summary", {})
            score_comparison = comparison.get("score_comparison", {})

            # Résumé compact
            summary = {
                "has_history": history["total_disbursed"] > 0,
                "previous_credits_count": history["total_disbursed"],
                "active_credits_count": history["active_loans_count"],
                "repayment_rate": history["repayment_rate"],
                "score_trend": score_comparison.get("score_evolution", {}).get("trend"),
                "recommendation": recommendation_summary.get("renewal_recommended"),
                "risk_level": recommendation_summary.get("risk_level"),
                "main_alerts": eligibility["alerts"][:3],  # Top 3 alertes
                "positive_indicators": recommendation_summary.get(
                    "positive_indicators_count", 0
                ),
                "warning_indicators": recommendation_summary.get(
                    "warning_indicators_count", 0
                ),
            }

            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Erreur résumé comparaison dossier {pk}: {e}",
                exc_info=True,
            )
            raise ValidationError({"detail": str(e)}) from e
