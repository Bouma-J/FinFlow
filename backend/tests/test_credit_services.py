"""Tests des services de crédit (simulation d'amortissement)."""
from decimal import Decimal

from apps.credits.services import compute_amortization_schedule


def test_amortization_schedule_totals():
    schedule = compute_amortization_schedule(Decimal("1200000"), Decimal("12"), 12)
    assert len(schedule) == 12
    total_principal = sum(row["principal"] for row in schedule)
    assert total_principal == Decimal("1200000.00")
    total_interest = sum(row["interest"] for row in schedule)
    assert total_interest > 0
    # Hors épargne : institution_due = principal + interest
    assert all(
        row["institution_due"] == row["principal"] + row["interest"]
        for row in schedule
    )


def test_amortization_zero_rate():
    schedule = compute_amortization_schedule(Decimal("1200"), Decimal("0"), 12)
    total_principal = sum(row["principal"] for row in schedule)
    assert total_principal == Decimal("1200.00")
    assert all(row["interest"] == Decimal("0.00") for row in schedule)


def test_amortization_degressive_principal():
    schedule = compute_amortization_schedule(
        Decimal("1200000"), Decimal("12"), 12, mechanism="DEGRESSIVE"
    )
    assert len(schedule) == 12
    assert sum(row["principal"] for row in schedule) == Decimal("1200000.00")


def test_amortization_in_fine():
    schedule = compute_amortization_schedule(
        Decimal("1000000"), Decimal("12"), 12, mechanism="IN_FINE"
    )
    assert len(schedule) == 12
    assert all(row["principal"] == 0 for row in schedule[:-1])
    assert schedule[-1]["principal"] == Decimal("1000000.00")


def test_amortization_bullet():
    schedule = compute_amortization_schedule(
        Decimal("1000000"), Decimal("12"), 12, mechanism="BULLET"
    )
    assert len(schedule) == 1
    assert schedule[0]["principal"] == Decimal("1000000.00")


def test_savings_excluded_from_institution_due():
    schedule = compute_amortization_schedule(
        Decimal("1000000"), Decimal("12"), 12, savings_rate=Decimal("5")
    )
    assert schedule[0]["savings"] > 0
    assert schedule[0]["institution_due"] == (
        schedule[0]["principal"] + schedule[0]["interest"]
    )
    assert schedule[0]["total"] == (
        schedule[0]["institution_due"] + schedule[0]["savings"]
    )
