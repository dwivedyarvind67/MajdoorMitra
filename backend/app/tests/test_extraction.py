"""
Tests for ExtractionService and Pydantic validation.
Verifies that:
- Information is correctly structured.
- Missing fields are deterministically detected.
- Values are never invented.
- Financial values are converted to Decimals.
"""

from decimal import Decimal
import pytest
from app.services.extraction_service import ExtractionService, ExtractionResult


def test_complete_work_extraction():
    svc = ExtractionService()
    raw_data = {
        "intent": "log_work",
        "days_worked": 6,
        "daily_wage": "700.00",
        "work_date": "2026-11-10",
        "employer_name": "Sharma Ji",
        "missing_fields": [],
        "ambiguities": [],
    }
    result = svc.validate_and_fill(raw_data)
    assert result.days_worked == Decimal("6")
    assert result.daily_wage == Decimal("700.00")
    assert result.work_date == "2026-11-10"
    assert result.employer_name == "Sharma Ji"
    assert result.missing_fields == []
    assert result.requires_confirmation is True


def test_missing_wage_detection():
    svc = ExtractionService()
    raw_data = {
        "intent": "log_work",
        "days_worked": 5,
        "work_date": "2026-11-10",
        "daily_wage": None,
    }
    result = svc.validate_and_fill(raw_data)
    assert result.days_worked == Decimal("5")
    assert result.daily_wage is None
    assert "daily_wage" in result.missing_fields


def test_missing_days_detection():
    svc = ExtractionService()
    raw_data = {
        "intent": "log_work",
        "days_worked": None,
        "daily_wage": "800.00",
        "work_date": "2026-11-10",
    }
    result = svc.validate_and_fill(raw_data)
    assert result.days_worked is None
    assert result.daily_wage == Decimal("800.00")
    assert "days_worked" in result.missing_fields


def test_never_invent_missing_values():
    svc = ExtractionService()
    raw_data = {
        "intent": "log_work",
    }
    result = svc.validate_and_fill(raw_data)
    assert result.days_worked is None
    assert result.daily_wage is None
    assert result.amount_received is None
    assert "days_worked" in result.missing_fields
    assert "daily_wage" in result.missing_fields


def test_invalid_money_precision_is_asked_again():
    result = ExtractionService().validate_and_fill({
        "intent": "log_work",
        "days_worked": "2",
        "daily_wage": "700.001",
        "work_date": "2026-11-10",
    })
    assert result.daily_wage is None
    assert "daily_wage" in result.missing_fields
    assert any("decimal places" in item for item in result.ambiguities)


def test_zero_quantity_and_zero_payment_cannot_become_ledger_records():
    svc = ExtractionService()
    no_work = svc.validate_and_fill({
        "intent": "log_work", "days_worked": 0, "daily_wage": 700, "work_date": "2026-11-10",
    })
    no_payment = svc.validate_and_fill({
        "intent": "log_payment", "amount_received": 0, "payment_type": "cash", "work_date": "2026-11-10",
    })
    assert "days_worked" in no_work.missing_fields
    assert no_payment.amount_received is None
    assert "amount_received" in no_payment.missing_fields


def test_hourly_extraction_requires_an_explicit_rate_and_computes_total():
    result = ExtractionService().validate_and_fill({
        "intent": "log_work",
        "wage_basis": "hourly",
        "hours_worked": "10",
        "hourly_rate": "100",
        "overtime_hours": "2",
        "work_date": "2026-11-10",
    })
    assert result.missing_fields == []
    assert result.calculated_total == Decimal("1100.00")

    missing_rate = ExtractionService().validate_and_fill({
        "intent": "log_work",
        "wage_basis": "hourly",
        "hours_worked": "10",
        "work_date": "2026-11-10",
    })
    assert "hourly_rate" in missing_rate.missing_fields


def test_overtime_above_reported_hours_requires_clarification():
    result = ExtractionService().validate_and_fill({
        "intent": "log_work",
        "wage_basis": "hourly",
        "hours_worked": "4",
        "hourly_rate": "100",
        "overtime_hours": "5",
        "work_date": "2026-11-10",
    })
    assert "overtime_hours" in result.missing_fields
    assert result.calculated_total is None
