"""Validate model output before it can become a worker-confirmable record."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.services.wage_calculator import FinancialService


class ExtractionResult(BaseModel):
    intent: Optional[str] = None
    days_worked: Optional[Decimal] = None
    daily_wage: Optional[Decimal] = None
    hours_worked: Optional[Decimal] = None
    wage_basis: str = "daily"
    hourly_rate: Optional[Decimal] = None
    overtime_hours: Decimal = Decimal("0")
    overtime_multiplier: Decimal = Decimal("1.5")
    base_earned: Optional[Decimal] = None
    overtime_earned: Optional[Decimal] = None
    calculated_total: Optional[Decimal] = None
    possible_duplicates: list[dict[str, Any]] = Field(default_factory=list)
    work_date: Optional[str] = None
    amount_received: Optional[Decimal] = None
    payment_type: Optional[str] = None
    employer_name: Optional[str] = None
    description: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True


class ExtractionService:
    """Turn untrusted AI output into a complete or explicitly incomplete record."""

    VALID_INTENTS = {"log_work", "log_payment"}
    VALID_PAYMENT_TYPES = {"cash", "upi", "bank", "advance", "other"}
    NUMERIC_FIELDS = (
        "days_worked", "daily_wage", "hours_worked", "hourly_rate",
        "overtime_hours", "overtime_multiplier", "amount_received",
    )
    MAX_MONEY = Decimal("9999999999999.99")

    def validate_and_fill(self, raw_data: dict[str, Any]) -> ExtractionResult:
        """Validate recognized values and mark every required omission for follow-up."""
        if not isinstance(raw_data, dict):
            raise ValueError("Extraction output must be a JSON object.")

        ambiguities = self._string_list(raw_data.get("ambiguities"))
        model_missing = set(self._string_list(raw_data.get("missing_fields")))
        for field, limit in (("employer_name", 255), ("description", 500)):
            raw_value = raw_data.get(field)
            if isinstance(raw_value, str) and len(raw_value.strip()) > limit:
                raise ValueError(f"{field} exceeds the supported length.")

        raw_intent = raw_data.get("intent")
        intent = raw_intent if raw_intent in self.VALID_INTENTS else "unknown"
        if intent == "unknown":
            model_missing.add("intent")
            if raw_intent not in (None, "", "unknown", "query"):
                ambiguities.append("The requested record type was not understood.")
            elif raw_intent in ("unknown", "query"):
                model_missing.add("intent")

        values: dict[str, Any] = {"intent": intent}
        for field in self.NUMERIC_FIELDS:
            value = self._safe_decimal(raw_data.get(field))
            if value is not None and (not value.is_finite() or value < 0):
                ambiguities.append(f"{field} must be a non-negative number.")
                value = None
            if value is not None and value.as_tuple().exponent < -2:
                ambiguities.append(f"{field} cannot have more than two decimal places.")
                value = None
            if field in {"daily_wage", "hourly_rate", "amount_received"} and value is not None and value > self.MAX_MONEY:
                ambiguities.append(f"{field} exceeds the supported amount range.")
                value = None
            if value is None and raw_data.get(field) not in (None, ""):
                ambiguities.append(f"{field} could not be read as a number.")
                model_missing.add(field)
            values[field] = value

        if values["days_worked"] is not None and values["days_worked"] > 31:
            ambiguities.append("days_worked cannot exceed 31 days.")
            values["days_worked"] = None
        if values["hours_worked"] is not None and values["hours_worked"] > 24:
            ambiguities.append("hours_worked cannot exceed 24 hours.")
            values["hours_worked"] = None

        wage_basis = raw_data.get("wage_basis", "daily")
        if wage_basis not in {"daily", "hourly"}:
            ambiguities.append("wage_basis must be daily or hourly.")
            wage_basis = "daily"
            model_missing.add("wage_basis")
        values["wage_basis"] = wage_basis
        if values["overtime_hours"] is None and raw_data.get("overtime_hours") in (None, ""):
            values["overtime_hours"] = Decimal("0")
        if values["overtime_multiplier"] is None and raw_data.get("overtime_multiplier") in (None, ""):
            values["overtime_multiplier"] = Decimal("1.5")
        if (
            values["overtime_multiplier"] is not None
            and (values["overtime_multiplier"] < 1 or values["overtime_multiplier"] > 3)
        ):
            ambiguities.append("overtime_multiplier must be between 1 and 3.")
            values["overtime_multiplier"] = None
            model_missing.add("overtime_multiplier")

        work_date = self._safe_date(raw_data.get("work_date"))
        if raw_data.get("work_date") not in (None, "") and work_date is None:
            ambiguities.append("The date could not be read. Please provide it as a date.")
        values["work_date"] = work_date.isoformat() if work_date else None

        payment_type = raw_data.get("payment_type")
        if payment_type not in self.VALID_PAYMENT_TYPES:
            if payment_type not in (None, ""):
                ambiguities.append("The payment method was not recognized.")
            payment_type = None
        values["payment_type"] = payment_type

        for field in ("employer_name", "description"):
            value = raw_data.get(field)
            values[field] = value.strip() if isinstance(value, str) and value.strip() else None

        required = {
            "log_work": (
                ("hours_worked", "hourly_rate", "work_date")
                if wage_basis == "hourly"
                else ("days_worked", "daily_wage", "work_date")
            ),
            # A payment date is shown for confirmation and is never silently invented.
            "log_payment": ("amount_received", "payment_type", "work_date"),
        }.get(intent, ())

        if intent == "log_payment" and values["amount_received"] == 0:
            ambiguities.append("A payment amount must be greater than zero.")
            values["amount_received"] = None

        missing_fields: list[str] = []
        if intent == "unknown":
            missing_fields.append("intent")
        else:
            for field in required:
                value = values.get(field)
                if value is None or field in model_missing:
                    missing_fields.append(field)
            for field in ("wage_basis", "overtime_hours", "overtime_multiplier"):
                if field in model_missing:
                    missing_fields.append(field)
            if (
                intent == "log_work"
                and wage_basis == "daily"
                and values["days_worked"] == 0
                and (values["hours_worked"] is None or values["hours_worked"] == 0)
            ):
                missing_fields.append("days_worked")
            if (
                intent == "log_work"
                and wage_basis == "hourly"
                and values["hours_worked"] is not None
                and values["overtime_hours"] is not None
                and values["overtime_hours"] > values["hours_worked"]
            ):
                ambiguities.append("overtime_hours cannot exceed hours_worked.")
                missing_fields.append("overtime_hours")

        calculated_total = None
        base_earned = None
        overtime_earned = None
        if intent == "log_work" and not missing_fields:
            try:
                breakdown = FinancialService.calculate_work_breakdown(
                    days_worked=values["days_worked"] or Decimal("0"),
                    daily_wage=values["daily_wage"],
                    hours_worked=values["hours_worked"],
                    wage_basis=wage_basis,
                    hourly_rate=values["hourly_rate"],
                    overtime_hours=values["overtime_hours"],
                    overtime_multiplier=values["overtime_multiplier"],
                )
                base_earned = breakdown["base_earned"]
                overtime_earned = breakdown["overtime_earned"]
                calculated_total = breakdown["total_earned"]
            except ValueError as exc:
                ambiguities.append(str(exc))
                candidate_field = "overtime_hours" if "overtime" in str(exc) else "hourly_rate"
                if candidate_field not in missing_fields:
                    missing_fields.append(candidate_field)

        return ExtractionResult(
            **values,
            base_earned=base_earned,
            overtime_earned=overtime_earned,
            calculated_total=calculated_total,
            missing_fields=list(dict.fromkeys(missing_fields)),
            ambiguities=list(dict.fromkeys(ambiguities)),
            requires_confirmation=True,
        )

    @staticmethod
    def _safe_decimal(value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _safe_date(value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item.strip()[:300] for item in value if isinstance(item, str) and item.strip()]


def get_extraction_service() -> ExtractionService:
    return ExtractionService()
