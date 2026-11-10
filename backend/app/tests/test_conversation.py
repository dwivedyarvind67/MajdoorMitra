"""
Tests for ConversationService:
- State transitions (INITIAL -> TRANSCRIBED -> EXTRACTED -> AWAITING_INFORMATION -> READY_FOR_CONFIRMATION)
- Hindi follow-up question generation
- Parsing user replies and numeric corrections
"""

from decimal import Decimal
from app.services.conversation_service import ConversationService


def test_awaiting_information_when_wage_missing():
    svc = ConversationService()
    extracted = {
        "intent": "log_work",
        "days_worked": "5",
        "missing_fields": ["daily_wage"],
    }
    state = svc.get_next_state("EXTRACTED", extracted)
    assert state == "AWAITING_INFORMATION"

    question = svc.generate_question(["daily_wage"], language="hi")
    assert question is not None
    assert "दैनिक मज़दूरी" in question or "मज़दूरी" in question


def test_ready_for_confirmation_when_complete():
    svc = ConversationService()
    extracted = {
        "intent": "log_work",
        "days_worked": "6",
        "daily_wage": "700.00",
        "work_date": "2026-11-10",
        "missing_fields": [],
    }
    state = svc.get_next_state("EXTRACTED", extracted)
    assert state == "READY_FOR_CONFIRMATION"

    msg = svc.generate_confirmation_message(extracted, language="hi")
    assert "पुष्टि" in msg or "सही है" in msg


def test_update_from_numeric_reply():
    svc = ConversationService()
    extracted = {
        "intent": "log_work",
        "days_worked": "5",
        "missing_fields": ["daily_wage"],
    }
    updated = svc.update_from_reply(extracted, "700 rupaye", ["daily_wage"])
    assert updated.get("daily_wage") == "700"
    assert "daily_wage" not in updated.get("missing_fields", [])


def test_apply_correction():
    svc = ConversationService()
    extracted = {
        "intent": "log_work",
        "days_worked": "5",
        "daily_wage": "700.00",
        "missing_fields": [],
    }
    updated = svc.apply_correction(extracted, "daily_wage", "750.00")
    assert updated["daily_wage"] == "750.00"


def test_hourly_overtime_summary_uses_the_shared_financial_calculation():
    message = ConversationService().generate_confirmation_message({
        "intent": "log_work",
        "wage_basis": "hourly",
        "days_worked": "0",
        "hours_worked": "10",
        "hourly_rate": "100",
        "overtime_hours": "2",
        "overtime_multiplier": "1.5",
        "work_date": "2026-11-10",
    }, "en")
    assert "Hours: 10 × ₹100 per hour" in message
    assert "Overtime earnings: ₹300.00" in message
    assert "Total earned: ₹1100.00" in message
