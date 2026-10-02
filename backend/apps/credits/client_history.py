"""Service de gestion de l'historique crédit client et éligibilité au renouvellement."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from apps.credits.models import CreditApplication, Loan
from apps.credits.renewal_policy import CreditRenewalPolicy

logger = logging.getLogger("finflow.credits")


class ClientHistoryService:
    """Service de récupération et analyse de l'historique crédit d'un client."""

    def __init__(self, client_id: int, tenant_id: str):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.policy = CreditRenewalPolicy.for_tenant(tenant_id)

    def get_credit_history(self) -> Dict[str, Any]:
        """Récupère l'historique complet des crédits du client."""
        
        # Récupérer tous les crédits du client
        applications = CreditApplication.objects.filter(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
        ).select_related("loan").order_by("-created_at")

        # Calculer les statistiques globales
        disbursed_apps = applications.filter(status="DISBURSED")
        loans = Loan.objects.filter(
            application__client_id=self.client_id,
            application__tenant_id=self.tenant_id,
        )

        # Calcul du taux de remboursement global
        total_principal = sum(
            Decimal(loan.principal) for loan in loans
        )
        total_repaid = self._calculate_total_repaid(loans)
        repayment_rate = (
            (total_repaid / total_principal * Decimal("100"))
            if total_principal > 0
            else Decimal("0")
        )

        # Solde restant dû sur prêts actifs
        active_loans = loans.filter(status="ACTIVE")
        current_outstanding = self._calculate_current_outstanding(active_loans)

        # Vérifier les situations problématiques
        has_litigation = self._check_litigation()
        has_dation = self._check_dation()
        has_restructuring = self._check_restructuring()
        has_writeoff = self._check_writeoff()

        # Historique de retards
        max_days_late = self._get_max_days_late(loans)

        # Dernier décaissement
        last_disbursement = disbursed_apps.first()
        last_disbursement_date = (
            last_disbursement.disbursed_at
            if last_disbursement and last_disbursement.disbursed_at
            else None
        )

        # Dernier prêt clôturé
        last_closed_loan = loans.filter(status="CLOSED").order_by("-created_at").first()
        last_closure_date = last_closed_loan.created_at if last_closed_loan else None

        return {
            "client_id": self.client_id,
            "total_applications": applications.count(),
            "total_disbursed": disbursed_apps.count(),
            "active_loans_count": active_loans.count(),
            "closed_loans_count": loans.filter(status="CLOSED").count(),
            
            # Montants
            "total_borrowed": float(total_principal),
            "total_repaid": float(total_repaid),
            "repayment_rate": float(repayment_rate),
            "current_outstanding": float(current_outstanding),
            
            # Situations problématiques
            "has_litigation": has_litigation,
            "has_dation": has_dation,
            "has_restructuring": has_restructuring,
            "has_writeoff": has_writeoff,
            
            # Retards
            "max_days_late_history": max_days_late,
            
            # Dates
            "last_disbursement_date": (
                last_disbursement_date.isoformat()
                if last_disbursement_date
                else None
            ),
            "last_closure_date": (
                last_closure_date.isoformat() if last_closure_date else None
            ),
            
            # Liste des prêts
            "loans": [
                {
                    "id": loan.id,
                    "application_reference": loan.application.reference,
                    "principal": float(loan.principal),
                    "disbursed_at": loan.disbursed_at.isoformat(),
                    "status": loan.status,
                }
                for loan in loans
            ],
        }

    def check_renewal_eligibility(self) -> Dict[str, Any]:
        """Vérifie l'éligibilité du client au renouvellement."""
        
        history = self.get_credit_history()
        alerts = []
        is_eligible = True

        # Vérifier le taux de remboursement
        repayment_rate = Decimal(str(history["repayment_rate"]))
        min_rate = self.policy.min_repayment_rate
        
        if repayment_rate < min_rate:
            if self.policy.block_if_below_repayment_threshold:
                is_eligible = False
                alerts.append({
                    "level": "ERROR",
                    "category": "REPAYMENT_RATE",
                    "message": (
                        f"Taux de remboursement insuffisant : {repayment_rate:.1f}% "
                        f"(minimum requis : {min_rate:.1f}%)"
                    ),
                    "blocking": True,
                })
            else:
                alerts.append({
                    "level": "WARNING",
                    "category": "REPAYMENT_RATE",
                    "message": (
                        f"Taux de remboursement faible : {repayment_rate:.1f}% "
                        f"(recommandé : {min_rate:.1f}%)"
                    ),
                    "blocking": False,
                })

        # Vérifier les contentieux
        if history["has_litigation"]:
            if self.policy.block_if_active_litigation:
                is_eligible = False
                alerts.append({
                    "level": "ERROR",
                    "category": "LITIGATION",
                    "message": "Le client a un contentieux actif",
                    "blocking": True,
                })
            else:
                alerts.append({
                    "level": "WARNING",
                    "category": "LITIGATION",
                    "message": "Le client a un contentieux actif",
                    "blocking": False,
                })

        # Vérifier les dations
        if history["has_dation"]:
            if self.policy.block_if_active_dation:
                is_eligible = False
                alerts.append({
                    "level": "ERROR",
                    "category": "DATION",
                    "message": "Le client a une dation en paiement en cours",
                    "blocking": True,
                })
            else:
                alerts.append({
                    "level": "WARNING",
                    "category": "DATION",
                    "message": "Le client a une dation en paiement en cours",
                    "blocking": False,
                })

        # Vérifier les restructurations récentes
        if history["has_restructuring"]:
            if self.policy.block_if_recent_restructuring:
                is_eligible = False
                alerts.append({
                    "level": "ERROR",
                    "category": "RESTRUCTURING",
                    "message": "Le client a eu une restructuration récente (< 12 mois)",
                    "blocking": True,
                })
            else:
                alerts.append({
                    "level": "WARNING",
                    "category": "RESTRUCTURING",
                    "message": "Le client a eu une restructuration récente",
                    "blocking": False,
                })

        # Vérifier les write-offs
        if history["has_writeoff"]:
            if self.policy.block_if_writeoff_history:
                is_eligible = False
                alerts.append({
                    "level": "ERROR",
                    "category": "WRITEOFF",
                    "message": "Le client a un crédit passé en perte dans son historique",
                    "blocking": True,
                })
            else:
                alerts.append({
                    "level": "WARNING",
                    "category": "WRITEOFF",
                    "message": "Le client a un crédit passé en perte dans son historique",
                    "blocking": False,
                })

        # Vérifier les crédits actifs
        active_count = history["active_loans_count"]
        if active_count > 0 and self.policy.block_if_active_loan:
            is_eligible = False
            alerts.append({
                "level": "ERROR",
                "category": "ACTIVE_LOAN",
                "message": f"Le client a déjà {active_count} crédit(s) actif(s)",
                "blocking": True,
            })
        elif active_count >= 2 and self.policy.warn_if_multiple_active_loans:
            alerts.append({
                "level": "WARNING",
                "category": "ACTIVE_LOAN",
                "message": f"Le client a {active_count} crédits actifs",
                "blocking": False,
            })

        # Vérifier les retards
        max_days_late = history["max_days_late_history"]
        if max_days_late > self.policy.max_days_late_allowed:
            alerts.append({
                "level": "WARNING",
                "category": "LATE_PAYMENT",
                "message": (
                    f"Retard maximum constaté : {max_days_late} jours "
                    f"(seuil : {self.policy.max_days_late_allowed} jours)"
                ),
                "blocking": False,
            })
        elif max_days_late > 0 and self.policy.warn_if_late_payment:
            alerts.append({
                "level": "INFO",
                "category": "LATE_PAYMENT",
                "message": f"Retards constatés : {max_days_late} jours maximum",
                "blocking": False,
            })

        # Vérifier le délai depuis le dernier décaissement
        if history["last_disbursement_date"]:
            last_disbursement = datetime.fromisoformat(
                history["last_disbursement_date"]
            )
            months_since = (timezone.now() - last_disbursement).days / 30
            min_months = self.policy.min_months_since_last_disbursement
            
            if months_since < min_months:
                alerts.append({
                    "level": "WARNING",
                    "category": "TIMING",
                    "message": (
                        f"Dernier décaissement récent : il y a {months_since:.0f} mois "
                        f"(recommandé : {min_months} mois minimum)"
                    ),
                    "blocking": False,
                })

        # Messages positifs si bon historique
        if not alerts and history["total_disbursed"] > 0:
            alerts.append({
                "level": "SUCCESS",
                "category": "HISTORY",
                "message": (
                    f"Excellent historique : {history['total_disbursed']} crédit(s) "
                    f"avec un taux de remboursement de {repayment_rate:.1f}%"
                ),
                "blocking": False,
            })

        return {
            "eligible": is_eligible,
            "alerts": alerts,
            "repayment_rate": float(repayment_rate),
            "history_summary": {
                "total_credits": history["total_disbursed"],
                "active_credits": history["active_loans_count"],
                "max_days_late": max_days_late,
            },
        }

    def _calculate_total_repaid(self, loans) -> Decimal:
        """Calcule le montant total remboursé sur tous les prêts."""
        total = Decimal("0")
        for loan in loans:
            # Somme des échéances payées
            paid = loan.installments.filter(
                status__in=["PAID", "PARTIAL"]
            ).aggregate(
                total=Sum("amount_paid")
            )["total"] or Decimal("0")
            total += paid
        return total

    def _calculate_current_outstanding(self, active_loans) -> Decimal:
        """Calcule le solde restant dû sur les prêts actifs."""
        total = Decimal("0")
        for loan in active_loans:
            # Principal - somme des échéances payées (part capital)
            paid = loan.installments.filter(
                status__in=["PAID", "PARTIAL"]
            ).aggregate(
                total=Sum("principal_due")
            )["total"] or Decimal("0")
            outstanding = Decimal(loan.principal) - paid
            total += max(outstanding, Decimal("0"))
        return total

    def _check_litigation(self) -> bool:
        """Vérifie si le client a un contentieux actif."""
        try:
            from apps.collections.models import Litigation
            return Litigation.objects.filter(
                case__loan__application__client_id=self.client_id,
                case__loan__application__tenant_id=self.tenant_id,
                status__in=["PENDING", "IN_PROGRESS"],
            ).exists()
        except ImportError:
            return False

    def _check_dation(self) -> bool:
        """Vérifie si le client a une dation en cours."""
        try:
            from apps.dations.models import Dation
            return Dation.objects.filter(
                loan__application__client_id=self.client_id,
                loan__application__tenant_id=self.tenant_id,
                status__in=["PENDING", "IN_PROGRESS"],
            ).exists()
        except ImportError:
            return False

    def _check_restructuring(self) -> bool:
        """Vérifie si le client a eu une restructuration récente (< 12 mois)."""
        twelve_months_ago = timezone.now() - timedelta(days=365)
        
        # Vérifier les restructurations via le nouveau modèle
        try:
            from apps.credits.loan_operations import LoanRestructuringRequest
            return LoanRestructuringRequest.objects.filter(
                loan__application__client_id=self.client_id,
                loan__application__tenant_id=self.tenant_id,
                status="EXECUTED",
                executed_at__gte=twelve_months_ago,
            ).exists()
        except ImportError:
            pass
        
        # Fallback : vérifier via l'ancien système collections
        try:
            from apps.collections.models import LoanRestructure
            return LoanRestructure.objects.filter(
                loan__application__client_id=self.client_id,
                loan__application__tenant_id=self.tenant_id,
                applied_at__gte=twelve_months_ago,
            ).exists()
        except ImportError:
            return False

    def _check_writeoff(self) -> bool:
        """Vérifie si le client a un crédit passé en perte."""
        # Vérifier via le nouveau modèle
        try:
            from apps.credits.loan_operations import LoanWriteOffRequest
            return LoanWriteOffRequest.objects.filter(
                loan__application__client_id=self.client_id,
                loan__application__tenant_id=self.tenant_id,
                status="EXECUTED",
            ).exists()
        except ImportError:
            pass
        
        # Fallback : vérifier via le statut du loan
        return Loan.objects.filter(
            application__client_id=self.client_id,
            application__tenant_id=self.tenant_id,
            status="DEFAULTED",
        ).exists()

    def _get_max_days_late(self, loans) -> int:
        """Retourne le nombre maximum de jours de retard constaté."""
        max_late = 0
        
        for loan in loans:
            # Vérifier les échéances en retard
            overdue_installments = loan.installments.filter(
                status__in=["OVERDUE", "PARTIAL"],
                due_date__lt=timezone.now().date(),
            )
            
            for inst in overdue_installments:
                days_late = (timezone.now().date() - inst.due_date).days
                max_late = max(max_late, days_late)
        
        return max_late
