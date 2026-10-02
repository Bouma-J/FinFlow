"""Service de comparaison détaillée des analyses financières."""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.credits.models import (
    CreditApplication,
    FinancialAnalysis,
    Loan,
)

logger = logging.getLogger("finflow.credits")


def _safe_decimal(value) -> Decimal:
    """Convertit une valeur en Decimal en gérant None."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _calculate_change_pct(old_value, new_value) -> Optional[Decimal]:
    """Calcule le pourcentage de changement entre deux valeurs."""
    old = _safe_decimal(old_value)
    new = _safe_decimal(new_value)
    
    if old == 0:
        if new == 0:
            return Decimal("0")
        return None  # Impossible de calculer si ancienne valeur = 0
    
    return ((new - old) / old * Decimal("100")).quantize(Decimal("0.01"))


def _format_evolution(old_value, new_value, threshold: Decimal = Decimal("15")) -> Dict:
    """Formate l'évolution d'une valeur avec indication de tendance."""
    change_pct = _calculate_change_pct(old_value, new_value)
    
    if change_pct is None:
        trend = "NEW"
    elif change_pct > threshold:
        trend = "INCREASE"
    elif change_pct < -threshold:
        trend = "DECREASE"
    else:
        trend = "STABLE"
    
    return {
        "old_value": old_value,
        "new_value": new_value,
        "change_pct": float(change_pct) if change_pct else None,
        "trend": trend,
    }


class FinancialAnalysisComparison:
    """Service de comparaison détaillée des analyses financières d'un client."""

    def __init__(self, client_id: int, current_application_id: int, tenant_id: str):
        self.client_id = client_id
        self.current_application_id = current_application_id
        self.tenant_id = tenant_id
        
        # Récupérer toutes les analyses du client (hors application actuelle)
        self.previous_analyses = list(
            FinancialAnalysis.objects.filter(
                application__client_id=client_id,
                application__status__in=["DISBURSED", "CLOSED"],
                is_reference=True,
            )
            .exclude(application_id=current_application_id)
            .select_related("application", "application__loan")
            .order_by("application__disbursed_at")
        )
        
        # Récupérer l'analyse actuelle
        self.current_analysis = (
            FinancialAnalysis.objects.filter(
                application_id=current_application_id,
                is_reference=True,
            )
            .select_related("application")
            .first()
        )

    def get_complete_comparison(self) -> Dict[str, Any]:
        """Retourne la comparaison complète de toutes les analyses."""
        if not self.current_analysis:
            return {
                "error": "Aucune analyse de référence trouvée pour le dossier actuel"
            }

        return {
            "client_id": self.client_id,
            "current_application_id": self.current_application_id,
            "has_previous_analyses": len(self.previous_analyses) > 0,
            "previous_analyses_count": len(self.previous_analyses),
            
            # Listes des analyses
            "previous_analyses": self._format_previous_analyses(),
            "current_analysis": self._format_current_analysis(),
            
            # Comparaisons détaillées par catégorie
            "income_comparison": self._compare_income(),
            "expenses_comparison": self._compare_expenses(),
            "exploitation_comparison": self._compare_exploitation(),
            "balance_comparison": self._compare_balance(),
            "cash_flow_comparison": self._compare_cash_flow(),
            "debt_comparison": self._compare_debt(),
            "ratios_comparison": self._compare_ratios(),
            "guarantees_comparison": self._compare_guarantees(),
            "sector_comparison": self._compare_sector(),
            "es_comparison": self._compare_environmental_social(),
            "group_comparison": self._compare_group(),
            "score_comparison": self._compare_scores(),
            
            # Insights automatiques
            "key_insights": self._generate_insights(),
            "recommendation_summary": self._generate_recommendation_summary(),
        }

    def _format_previous_analyses(self) -> List[Dict]:
        """Formate les analyses antérieures pour l'API."""
        result = []
        for analysis in self.previous_analyses:
            app = analysis.application
            loan = getattr(app, "loan", None)
            
            result.append({
                "analysis_id": analysis.id,
                "application_id": app.id,
                "application_reference": app.reference,
                "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
                "disbursed_at": app.disbursed_at.isoformat() if app.disbursed_at else None,
                "amount_approved": str(app.amount_approved) if app.amount_approved else None,
                "loan_id": loan.id if loan else None,
                "loan_status": loan.status if loan else None,
                "internal_score": float(analysis.internal_score) if analysis.internal_score else None,
                "recommendation": analysis.recommendation,
            })
        
        return result

    def _format_current_analysis(self) -> Dict:
        """Formate l'analyse actuelle pour l'API."""
        analysis = self.current_analysis
        app = analysis.application
        
        return {
            "analysis_id": analysis.id,
            "application_id": app.id,
            "application_reference": app.reference,
            "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
            "amount_requested": str(app.amount_requested),
            "amount_proposed": str(app.amount_proposed) if app.amount_proposed else None,
            "internal_score": float(analysis.internal_score) if analysis.internal_score else None,
            "recommendation": analysis.recommendation,
        }

    def _compare_income(self) -> Dict[str, Any]:
        """Compare les revenus entre analyses (particulier)."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Calculer moyennes des analyses précédentes
        prev_salary = Decimal("0")
        prev_spouse = Decimal("0")
        prev_rental = Decimal("0")
        prev_activity = Decimal("0")
        prev_other = Decimal("0")
        
        for analysis in self.previous_analyses:
            prev_salary += _safe_decimal(analysis.salary_income)
            prev_spouse += _safe_decimal(analysis.spouse_income)
            prev_rental += _safe_decimal(analysis.rental_income)
            prev_activity += _safe_decimal(analysis.other_activity_income)
            prev_other += _safe_decimal(analysis.other_income)
        
        count = len(self.previous_analyses)
        prev_salary_avg = prev_salary / count if count > 0 else Decimal("0")
        prev_spouse_avg = prev_spouse / count if count > 0 else Decimal("0")
        prev_rental_avg = prev_rental / count if count > 0 else Decimal("0")
        prev_activity_avg = prev_activity / count if count > 0 else Decimal("0")
        prev_other_avg = prev_other / count if count > 0 else Decimal("0")
        prev_total_avg = prev_salary_avg + prev_spouse_avg + prev_rental_avg + prev_activity_avg + prev_other_avg

        # Valeurs actuelles
        curr = self.current_analysis
        curr_salary = _safe_decimal(curr.salary_income)
        curr_spouse = _safe_decimal(curr.spouse_income)
        curr_rental = _safe_decimal(curr.rental_income)
        curr_activity = _safe_decimal(curr.other_activity_income)
        curr_other = _safe_decimal(curr.other_income)
        curr_total = curr.total_income

        return {
            "salary_income": _format_evolution(prev_salary_avg, curr_salary),
            "spouse_income": _format_evolution(prev_spouse_avg, curr_spouse),
            "rental_income": _format_evolution(prev_rental_avg, curr_rental),
            "other_activity_income": _format_evolution(prev_activity_avg, curr_activity),
            "other_income": _format_evolution(prev_other_avg, curr_other),
            "total_income": _format_evolution(prev_total_avg, curr_total),
            "historical_values": [
                {
                    "application_reference": analysis.application.reference,
                    "salary_income": float(_safe_decimal(analysis.salary_income)),
                    "spouse_income": float(_safe_decimal(analysis.spouse_income)),
                    "rental_income": float(_safe_decimal(analysis.rental_income)),
                    "other_activity_income": float(_safe_decimal(analysis.other_activity_income)),
                    "other_income": float(_safe_decimal(analysis.other_income)),
                    "total_income": float(analysis.total_income),
                }
                for analysis in self.previous_analyses
            ],
        }

    def _compare_expenses(self) -> Dict[str, Any]:
        """Compare les charges entre analyses (particulier)."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Moyennes précédentes
        prev_rent = sum(_safe_decimal(a.rent_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_food = sum(_safe_decimal(a.food_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_utilities = sum(_safe_decimal(a.utilities_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_transport = sum(_safe_decimal(a.transport_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_education = sum(_safe_decimal(a.education_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_health = sum(_safe_decimal(a.health_expense) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_other = sum(_safe_decimal(a.other_household_expenses) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_total = sum(a.total_household_charges for a in self.previous_analyses) / len(self.previous_analyses)

        # Valeurs actuelles
        curr = self.current_analysis
        
        return {
            "rent_expense": _format_evolution(prev_rent, curr.rent_expense),
            "food_expense": _format_evolution(prev_food, curr.food_expense),
            "utilities_expense": _format_evolution(prev_utilities, curr.utilities_expense),
            "transport_expense": _format_evolution(prev_transport, curr.transport_expense),
            "education_expense": _format_evolution(prev_education, curr.education_expense),
            "health_expense": _format_evolution(prev_health, curr.health_expense),
            "other_household_expenses": _format_evolution(prev_other, curr.other_household_expenses),
            "total_charges": _format_evolution(prev_total, curr.total_household_charges),
        }

    def _compare_exploitation(self) -> Dict[str, Any]:
        """Compare le compte d'exploitation (entreprise)."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Moyennes précédentes
        prev_turnover = sum(_safe_decimal(a.turnover) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_cogs = sum(_safe_decimal(a.cogs) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_op_expenses = sum(_safe_decimal(a.total_operating_expenses) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_net_result = sum(_safe_decimal(a.net_result) for a in self.previous_analyses) / len(self.previous_analyses)
        prev_gross_margin = sum(_safe_decimal(a.gross_margin) for a in self.previous_analyses) / len(self.previous_analyses)

        # Valeurs actuelles
        curr = self.current_analysis

        return {
            "turnover": _format_evolution(prev_turnover, curr.turnover),
            "cogs": _format_evolution(prev_cogs, curr.cogs),
            "gross_margin": _format_evolution(prev_gross_margin, curr.gross_margin),
            "operating_expenses": _format_evolution(prev_op_expenses, curr.total_operating_expenses),
            "net_result": _format_evolution(prev_net_result, curr.net_result),
            "gross_margin_pct": _format_evolution(
                (prev_gross_margin / prev_turnover * 100) if prev_turnover > 0 else None,
                curr.gross_margin_pct,
            ),
            "net_margin_pct": _format_evolution(
                (prev_net_result / prev_turnover * 100) if prev_turnover > 0 else None,
                curr.net_margin_pct,
            ),
        }

    def _compare_balance(self) -> Dict[str, Any]:
        """Compare le bilan simplifié (entreprise)."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Moyennes précédentes
        count = len(self.previous_analyses)
        prev_assets = sum(_safe_decimal(a.total_assets) for a in self.previous_analyses) / count
        prev_debts = sum(_safe_decimal(a.total_debts) for a in self.previous_analyses) / count
        prev_equity = sum(_safe_decimal(a.equity) for a in self.previous_analyses) / count
        prev_bfr = sum(_safe_decimal(a.bfr) for a in self.previous_analyses) / count

        # Valeurs actuelles
        curr = self.current_analysis

        return {
            "total_assets": _format_evolution(prev_assets, curr.total_assets),
            "total_debts": _format_evolution(prev_debts, curr.total_debts),
            "equity": _format_evolution(prev_equity, curr.equity),
            "bfr": _format_evolution(prev_bfr, curr.bfr),
        }

    def _compare_cash_flow(self) -> Dict[str, Any]:
        """Compare la trésorerie prévisionnelle."""
        if not self.previous_analyses:
            return {"no_history": True}

        count = len(self.previous_analyses)
        prev_inflows = sum(_safe_decimal(a.projected_monthly_inflows) for a in self.previous_analyses) / count
        prev_outflows = sum(_safe_decimal(a.projected_monthly_outflows) for a in self.previous_analyses) / count
        prev_surplus = prev_inflows - prev_outflows

        curr = self.current_analysis
        curr_surplus = curr.projected_monthly_surplus

        return {
            "projected_inflows": _format_evolution(prev_inflows, curr.projected_monthly_inflows),
            "projected_outflows": _format_evolution(prev_outflows, curr.projected_monthly_outflows),
            "projected_surplus": _format_evolution(prev_surplus, curr_surplus),
        }

    def _compare_debt(self) -> Dict[str, Any]:
        """Compare l'endettement consolidé."""
        if not self.previous_analyses:
            return {"no_history": True}

        count = len(self.previous_analyses)
        prev_debt_monthly = sum(_safe_decimal(a.existing_debt_monthly) for a in self.previous_analyses) / count
        prev_active_loans = sum(a.active_loans_count for a in self.previous_analyses) / count

        curr = self.current_analysis

        return {
            "existing_debt_monthly": _format_evolution(prev_debt_monthly, curr.existing_debt_monthly),
            "active_loans_count": _format_evolution(prev_active_loans, curr.active_loans_count),
            "has_payment_incidents": {
                "previous": any(a.has_payment_incidents for a in self.previous_analyses),
                "current": curr.has_payment_incidents,
            },
            "max_days_late": {
                "previous_max": max((a.max_days_late or 0) for a in self.previous_analyses) if self.previous_analyses else 0,
                "current": curr.max_days_late or 0,
            },
        }

    def _compare_ratios(self) -> Dict[str, Any]:
        """Compare les ratios clés calculés."""
        if not self.previous_analyses:
            return {"no_history": True}

        count = len(self.previous_analyses)
        
        # Moyennes précédentes
        prev_installment = sum(_safe_decimal(a.new_installment) for a in self.previous_analyses) / count
        prev_capacity = sum(_safe_decimal(a.repayment_capacity) for a in self.previous_analyses) / count
        prev_debt_ratio = sum(_safe_decimal(a.debt_ratio) for a in self.previous_analyses) / count
        prev_dscr = sum(_safe_decimal(a.dscr) for a in self.previous_analyses if a.dscr) / max(1, sum(1 for a in self.previous_analyses if a.dscr))
        prev_coverage = sum(_safe_decimal(a.guarantee_coverage) for a in self.previous_analyses) / count

        # Valeurs actuelles
        curr = self.current_analysis

        return {
            "new_installment": _format_evolution(prev_installment, curr.new_installment),
            "repayment_capacity": _format_evolution(prev_capacity, curr.repayment_capacity),
            "debt_ratio": _format_evolution(prev_debt_ratio, curr.debt_ratio),
            "dscr": _format_evolution(prev_dscr, curr.dscr) if curr.dscr else None,
            "guarantee_coverage": _format_evolution(prev_coverage, curr.guarantee_coverage),
            "debt_ratio_stress": _format_evolution(
                sum(_safe_decimal(a.debt_ratio_stress) for a in self.previous_analyses if a.debt_ratio_stress) / max(1, sum(1 for a in self.previous_analyses if a.debt_ratio_stress)),
                curr.debt_ratio_stress,
            ) if curr.debt_ratio_stress else None,
            "dscr_stress": _format_evolution(
                sum(_safe_decimal(a.dscr_stress) for a in self.previous_analyses if a.dscr_stress) / max(1, sum(1 for a in self.previous_analyses if a.dscr_stress)),
                curr.dscr_stress,
            ) if curr.dscr_stress else None,
        }

    def _compare_guarantees(self) -> Dict[str, Any]:
        """Compare les garanties entre crédits."""
        # À implémenter avec le module guarantees
        return {"not_implemented": True}

    def _compare_sector(self) -> Dict[str, Any]:
        """Compare l'analyse sectorielle."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Comparaison qualitative
        prev_sectors = [a.sector for a in self.previous_analyses if a.sector]
        prev_risk_levels = [a.sector_risk_level for a in self.previous_analyses if a.sector_risk_level]

        curr = self.current_analysis

        return {
            "sector": {
                "previous": list(set(prev_sectors)),
                "current": curr.sector,
                "changed": curr.sector not in prev_sectors if prev_sectors else False,
            },
            "sector_risk_level": {
                "previous": list(set(prev_risk_levels)),
                "current": curr.sector_risk_level,
                "changed": curr.sector_risk_level not in prev_risk_levels if prev_risk_levels else False,
            },
        }

    def _compare_environmental_social(self) -> Dict[str, Any]:
        """Compare l'analyse environnementale et sociale."""
        if not self.previous_analyses:
            return {"no_history": True}

        prev_categories = [a.es_category for a in self.previous_analyses if a.es_category]
        prev_risk_levels = [a.es_risk_level for a in self.previous_analyses if a.es_risk_level]

        curr = self.current_analysis

        return {
            "es_category": {
                "previous": list(set(prev_categories)),
                "current": curr.es_category,
            },
            "es_risk_level": {
                "previous": list(set(prev_risk_levels)),
                "current": curr.es_risk_level,
            },
            "jobs_evolution": _format_evolution(
                sum((_safe_decimal(a.jobs_created) + _safe_decimal(a.jobs_maintained)) for a in self.previous_analyses) / len(self.previous_analyses),
                (_safe_decimal(curr.jobs_created) + _safe_decimal(curr.jobs_maintained)),
            ),
        }

    def _compare_group(self) -> Dict[str, Any]:
        """Compare les données de groupement."""
        if not self.previous_analyses:
            return {"no_history": True}

        count = len(self.previous_analyses)
        prev_members = sum(a.members_count or 0 for a in self.previous_analyses) / count
        prev_capacity = sum(_safe_decimal(a.collective_capacity) for a in self.previous_analyses) / count

        curr = self.current_analysis

        return {
            "members_count": _format_evolution(prev_members, curr.members_count),
            "collective_capacity": _format_evolution(prev_capacity, curr.collective_capacity),
        }

    def _compare_scores(self) -> Dict[str, Any]:
        """Compare les scores et recommandations."""
        if not self.previous_analyses:
            return {"no_history": True}

        # Évolution des scores
        scores_history = [
            {
                "application_reference": a.application.reference,
                "analysis_date": a.analysis_date.isoformat() if a.analysis_date else None,
                "internal_score": float(a.internal_score) if a.internal_score else None,
                "recommendation": a.recommendation,
            }
            for a in self.previous_analyses
        ]

        prev_score_avg = sum(_safe_decimal(a.internal_score) for a in self.previous_analyses if a.internal_score) / max(1, sum(1 for a in self.previous_analyses if a.internal_score))
        curr_score = _safe_decimal(self.current_analysis.internal_score)

        return {
            "score_evolution": _format_evolution(prev_score_avg, curr_score),
            "scores_history": scores_history,
            "current_score": float(curr_score) if curr_score else None,
            "current_recommendation": self.current_analysis.recommendation,
            "score_breakdown": self.current_analysis.score_breakdown,
        }

    def _generate_insights(self) -> List[Dict[str, str]]:
        """Génère des insights automatiques sur les changements significatifs."""
        insights = []

        if not self.previous_analyses:
            insights.append({
                "category": "HISTORY",
                "message": "Premier crédit de ce client dans l'institution",
                "severity": "INFO",
            })
            return insights

        # Insight sur le revenu total
        income_comp = self._compare_income()
        if income_comp.get("total_income", {}).get("trend") == "INCREASE":
            change = income_comp["total_income"].get("change_pct", 0)
            insights.append({
                "category": "INCOME",
                "message": f"Revenu total en hausse de {change:.1f}% par rapport aux crédits précédents",
                "severity": "POSITIVE",
            })
        elif income_comp.get("total_income", {}).get("trend") == "DECREASE":
            change = abs(income_comp["total_income"].get("change_pct", 0))
            insights.append({
                "category": "INCOME",
                "message": f"⚠️ Revenu total en baisse de {change:.1f}% par rapport aux crédits précédents",
                "severity": "WARNING",
            })

        # Insight sur le ratio d'endettement
        ratios_comp = self._compare_ratios()
        debt_ratio_data = ratios_comp.get("debt_ratio", {})
        if debt_ratio_data.get("trend") == "DECREASE":
            insights.append({
                "category": "DEBT",
                "message": "Amélioration du taux d'endettement",
                "severity": "POSITIVE",
            })
        elif debt_ratio_data.get("trend") == "INCREASE":
            insights.append({
                "category": "DEBT",
                "message": "⚠️ Augmentation du taux d'endettement",
                "severity": "WARNING",
            })

        # Insight sur le score
        score_comp = self._compare_scores()
        score_ev = score_comp.get("score_evolution", {})
        if score_ev.get("trend") == "INCREASE":
            change = score_ev.get("change_pct", 0)
            insights.append({
                "category": "SCORE",
                "message": f"Amélioration du score interne (+{change:.1f} points)",
                "severity": "POSITIVE",
            })
        elif score_ev.get("trend") == "DECREASE":
            change = abs(score_ev.get("change_pct", 0))
            insights.append({
                "category": "SCORE",
                "message": f"⚠️ Baisse du score interne (-{change:.1f} points)",
                "severity": "WARNING",
            })

        return insights

    def _generate_recommendation_summary(self) -> Dict[str, Any]:
        """Génère un résumé de recommandation basé sur la comparaison."""
        if not self.previous_analyses:
            return {
                "trend": "NEW",
                "risk_level": "UNKNOWN",
                "renewal_recommended": None,
                "comment": "Premier crédit, pas d'historique de comparaison",
            }

        # Analyser les tendances globales
        insights = self._generate_insights()
        positive_count = sum(1 for i in insights if i["severity"] == "POSITIVE")
        warning_count = sum(1 for i in insights if i["severity"] == "WARNING")

        if positive_count > warning_count:
            trend = "POSITIVE"
            risk_level = "LOW"
            renewal_recommended = True
            comment = "Évolution positive de la situation financière du client"
        elif warning_count > positive_count:
            trend = "NEGATIVE"
            risk_level = "MEDIUM"
            renewal_recommended = False
            comment = "Dégradation de certains indicateurs, vigilance recommandée"
        else:
            trend = "STABLE"
            risk_level = "LOW"
            renewal_recommended = True
            comment = "Situation financière stable"

        return {
            "trend": trend,
            "risk_level": risk_level,
            "renewal_recommended": renewal_recommended,
            "comment": comment,
            "positive_indicators_count": positive_count,
            "warning_indicators_count": warning_count,
        }
