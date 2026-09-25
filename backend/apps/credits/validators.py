"""
Validators pour le module credits, notamment pour l'analyse financière.
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError


def validate_detailed_data(value: Any) -> None:
    """
    Valide la structure JSON du champ detailed_data de FinancialAnalysis.
    
    Le detailed_data doit contenir des listes de périodes pour différentes catégories :
    - income_detail : Liste de IncomePeriod
    - expenses_detail : Liste de ExpensesPeriod
    - exploitation_detail : Liste de ExploitationPeriod
    - banking_detail : Liste de BankingPeriod
    - collective_detail : Liste de CollectivePeriod
    
    Chaque période est un dictionnaire avec :
    - period_label (optionnel) : str
    - Des champs numériques spécifiques à la catégorie
    
    Raises:
        ValidationError: Si la structure n'est pas valide
    """
    if value is None:
        return  # NULL est accepté
    
    if not isinstance(value, dict):
        raise ValidationError(
            "detailed_data doit être un objet JSON (dictionnaire), "
            f"pas {type(value).__name__}"
        )
    
    # Clés autorisées
    ALLOWED_KEYS = {
        'income_detail',
        'expenses_detail',
        'exploitation_detail',
        'banking_detail',
        'collective_detail',
    }
    
    # Vérifier les clés inconnues
    unknown_keys = set(value.keys()) - ALLOWED_KEYS
    if unknown_keys:
        raise ValidationError(
            f"Clés inconnues dans detailed_data : {', '.join(unknown_keys)}. "
            f"Clés autorisées : {', '.join(sorted(ALLOWED_KEYS))}"
        )
    
    # Valider chaque catégorie si présente
    if 'income_detail' in value:
        _validate_income_detail(value['income_detail'])
    
    if 'expenses_detail' in value:
        _validate_expenses_detail(value['expenses_detail'])
    
    if 'exploitation_detail' in value:
        _validate_exploitation_detail(value['exploitation_detail'])
    
    if 'banking_detail' in value:
        _validate_banking_detail(value['banking_detail'])
    
    if 'collective_detail' in value:
        _validate_collective_detail(value['collective_detail'])


def _validate_period_list(
    periods: Any,
    category_name: str,
    allowed_fields: set,
    required_fields: Optional[set] = None
) -> None:
    """
    Valide qu'une liste de périodes a la structure attendue.
    
    Args:
        periods: La liste à valider
        category_name: Nom de la catégorie (pour les messages d'erreur)
        allowed_fields: Ensemble des champs autorisés
        required_fields: Ensemble des champs requis (optionnel)
    """
    if not isinstance(periods, list):
        raise ValidationError(
            f"{category_name} doit être une liste, pas {type(periods).__name__}"
        )
    
    if len(periods) == 0:
        raise ValidationError(
            f"{category_name} ne peut pas être une liste vide. "
            "Utilisez null ou omettez la clé si pas de données."
        )
    
    if len(periods) > 36:  # Max 3 ans mensuels
        raise ValidationError(
            f"{category_name} contient trop de périodes ({len(periods)}). "
            "Maximum autorisé : 36 périodes."
        )
    
    for idx, period in enumerate(periods, start=1):
        if not isinstance(period, dict):
            raise ValidationError(
                f"{category_name}[{idx}] doit être un objet, "
                f"pas {type(period).__name__}"
            )
        
        # Vérifier les champs requis
        if required_fields:
            missing = required_fields - set(period.keys())
            if missing:
                raise ValidationError(
                    f"{category_name}[{idx}] : champs requis manquants : "
                    f"{', '.join(sorted(missing))}"
                )
        
        # Vérifier les champs inconnus
        unknown = set(period.keys()) - allowed_fields
        if unknown:
            raise ValidationError(
                f"{category_name}[{idx}] : champs inconnus : "
                f"{', '.join(sorted(unknown))}. "
                f"Champs autorisés : {', '.join(sorted(allowed_fields))}"
            )
        
        # Valider les types des valeurs numériques
        for key, val in period.items():
            if key == 'period_label':
                if val is not None and not isinstance(val, str):
                    raise ValidationError(
                        f"{category_name}[{idx}].period_label doit être "
                        f"une chaîne, pas {type(val).__name__}"
                    )
            else:
                # Tous les autres champs doivent être numériques ou null
                if val is not None:
                    if not isinstance(val, (int, float, Decimal)):
                        # Essayer de convertir string en nombre
                        try:
                            float(val)
                        except (ValueError, TypeError, InvalidOperation):
                            raise ValidationError(
                                f"{category_name}[{idx}].{key} doit être un nombre, "
                                f"pas {type(val).__name__} : {val!r}"
                            )


def _validate_income_detail(periods: Any) -> None:
    """Valide la structure de income_detail (revenus)."""
    ALLOWED_FIELDS = {
        'period_label',
        # Revenus salariés
        'salary_income',
        'spouse_income',
        'rental_income',
        'other_activity_income',
        'other_income',
        # AGR
        'activity_turnover',
        'activity_expenses',
    }
    
    _validate_period_list(periods, 'income_detail', ALLOWED_FIELDS)


def _validate_expenses_detail(periods: Any) -> None:
    """Valide la structure de expenses_detail (dépenses)."""
    ALLOWED_FIELDS = {
        'period_label',
        # Dépenses ménage
        'rent_expense',
        'food_expense',
        'utilities_expense',
        'transport_expense',
        'education_expense',
        'health_expense',
        'other_household_expenses',
        # Charges informelles
        'tontine_expense',
        'social_contributions',
        'family_support_expense',
    }
    
    _validate_period_list(periods, 'expenses_detail', ALLOWED_FIELDS)


def _validate_exploitation_detail(periods: Any) -> None:
    """Valide la structure de exploitation_detail (compte d'exploitation)."""
    ALLOWED_FIELDS = {
        'period_label',
        # Revenus & coûts
        'turnover',
        'cogs',
        # Charges d'exploitation
        'op_rent',
        'op_salaries',
        'op_utilities',
        'op_transport',
        'op_telecom',
        'op_taxes',
        'op_maintenance',
        'op_other',
        # Amortissement & financier
        'depreciation',
        'financial_charges',
        # Stocks
        'stock_value',
    }
    
    # Le turnover est souvent requis pour les entreprises
    # Mais on reste flexible pour permettre des saisies progressives
    _validate_period_list(periods, 'exploitation_detail', ALLOWED_FIELDS)


def _validate_banking_detail(periods: Any) -> None:
    """Valide la structure de banking_detail (mouvements bancaires)."""
    ALLOWED_FIELDS = {
        'period_label',
        'credit_movements',
        'debit_movements',
        'average_balance',
    }
    
    _validate_period_list(periods, 'banking_detail', ALLOWED_FIELDS)


def _validate_collective_detail(periods: Any) -> None:
    """Valide la structure de collective_detail (finances collectives groupement)."""
    ALLOWED_FIELDS = {
        'period_label',
        'contributions',
        'collective_savings',
        'solidarity_fund',
    }
    
    _validate_period_list(periods, 'collective_detail', ALLOWED_FIELDS)
