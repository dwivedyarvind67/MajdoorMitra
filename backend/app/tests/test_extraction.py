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
