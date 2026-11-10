"""
Wage Calculation Engine for MazdoorMitra.
Provides deterministic, precision financial calculations using Python's Decimal.
Never uses float for monetary amounts.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any


ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


def quantize_money(amount: Decimal | float | int | str | None) -> Decimal:
    """Ensure a financial value is a Decimal quantized to 2 decimal places."""
    if amount is None:
        return ZERO
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class WageCalculator:
    """Deterministic financial calculator for wage ledger."""

    @staticmethod
    def calculate_work_entry_total(
        days_worked: Decimal | float | int | str,
        daily_wage: Decimal | float | int | str,
        hours_worked: Optional[Decimal | float | int | str] = None,
        *,
        wage_basis: str = "daily",
        hourly_rate: Optional[Decimal | float | int | str] = None,
        overtime_hours: Decimal | float | int | str = 0,
        overtime_multiplier: Decimal | float | int | str = "1.5",
    ) -> Decimal:
        """
        Calculate total earned for a single work entry.
        Normally: days_worked * daily_wage.
        If days_worked is 0 and hours_worked is provided, calculate hourly based on standard 8-hour day.
        """
        return FinancialService.calculate_work_breakdown(
            days_worked=days_worked,
            daily_wage=daily_wage,
            hours_worked=hours_worked,
            wage_basis=wage_basis,
            hourly_rate=hourly_rate,
            overtime_hours=overtime_hours,
            overtime_multiplier=overtime_multiplier,
        )["total_earned"]

    @staticmethod
    def calculate_entry_total(days_worked: Decimal, daily_wage: Decimal) -> Decimal:
        """Alias for single work entry total calculation."""
        return WageCalculator.calculate_work_entry_total(days_worked, daily_wage)

    @staticmethod
    def calculate_total_earned(work_entries: List[Any]) -> Decimal:
        """Sum total_earned from a list of work entries."""
        total = ZERO
        for entry in work_entries:
            if hasattr(entry, "total_earned") and entry.total_earned is not None:
                amount = entry.total_earned
            elif isinstance(entry, dict) and "total_earned" in entry and entry["total_earned"] is not None:
                amount = entry["total_earned"]
            elif hasattr(entry, "days_worked") and hasattr(entry, "daily_wage"):
                amount = WageCalculator.calculate_work_entry_total(
                    entry.days_worked,
                    entry.daily_wage,
                    getattr(entry, "hours_worked", None),
                )
            elif isinstance(entry, dict) and "days_worked" in entry and "daily_wage" in entry:
                amount = WageCalculator.calculate_work_entry_total(
                    entry["days_worked"],
                    entry["daily_wage"],
                    entry.get("hours_worked"),
                )
            else:
                amount = ZERO
            total += Decimal(str(amount))
        return quantize_money(total)

    @staticmethod
    def calculate_total_received(payments: List[Any], include_advances: bool = True) -> Decimal:
        """
        Sum all eligible payments received by the worker.
        Advances are treated as payments received upfront.
        """
        total = ZERO
        for payment in payments:
            ptype = getattr(payment, "payment_type", None) or (payment.get("payment_type") if isinstance(payment, dict) else None)
            if not include_advances and ptype == "advance":
                continue
            amt = getattr(payment, "amount", None) or (payment.get("amount") if isinstance(payment, dict) else Decimal("0"))
            total += Decimal(str(amt))
        return quantize_money(total)

    @staticmethod
    def calculate_total_advances(payments: List[Any]) -> Decimal:
        """Sum only advance payments."""
        total = ZERO
        for payment in payments:
            ptype = getattr(payment, "payment_type", None) or (payment.get("payment_type") if isinstance(payment, dict) else None)
            if ptype == "advance":
                amt = getattr(payment, "amount", None) or (payment.get("amount") if isinstance(payment, dict) else Decimal("0"))
                total += Decimal(str(amt))
        return quantize_money(total)

    @staticmethod
    def calculate_balance(total_earned: Decimal, total_received: Decimal) -> Decimal:
        """
        Balance = Total Earned - Total Received.
        Positive: Worker is owed money.
        Negative: Worker was overpaid or has unadjusted advance.
        """
        if not isinstance(total_earned, Decimal):
            total_earned = Decimal(str(total_earned))
        if not isinstance(total_received, Decimal):
            total_received = Decimal(str(total_received))
        return quantize_money(total_earned - total_received)

    @staticmethod
    def calculate_pending(balance: Decimal) -> Decimal:
        """Pending wages owed to the worker = max(balance, 0)."""
        if not isinstance(balance, Decimal):
            balance = Decimal(str(balance))
        return max(quantize_money(balance), ZERO)

    @staticmethod
    def calculate_overpaid(balance: Decimal) -> Decimal:
        """Overpaid amount = max(-balance, 0)."""
        if not isinstance(balance, Decimal):
            balance = Decimal(str(balance))
        return max(quantize_money(-balance), ZERO)

    @staticmethod
    def calculate_total_work_days(work_entries: List[Any]) -> Decimal:
        """Sum total days worked across all entries."""
        total = ZERO
        for entry in work_entries:
            days = getattr(entry, "days_worked", None) or (entry.get("days_worked") if isinstance(entry, dict) else None)
            if days is not None:
                total += Decimal(str(days))
        return quantize_money(total)

    @classmethod
    def calculate_summary(
        cls,
        work_entries: List[Any],
        payments: List[Any],
    ) -> Dict[str, Any]:
        """
        Compute full deterministic ledger summary.
        Advances are tracked separately and accounted for exactly once in total_received.
        """
        earned = cls.calculate_total_earned(work_entries)
        received = cls.calculate_total_received(payments, include_advances=True)
        advances = cls.calculate_total_advances(payments)
        balance = cls.calculate_balance(earned, received)
        pending = cls.calculate_pending(balance)
        overpaid = cls.calculate_overpaid(balance)
        total_days = cls.calculate_total_work_days(work_entries)

        return {
            "total_earned": earned,
            "total_received": received,
            "total_advances": advances,
            "balance": balance,
            "pending": pending,
            "overpaid": overpaid,
            "total_days_worked": total_days,
            "total_work_days": total_days,
            "work_entries_count": len(work_entries),
            "payments_count": len(payments),
        }


class FinancialService:
    """Shared Decimal-only financial rules used by API, ledger and statements."""

    @staticmethod
    def _decimal(value: Decimal | float | int | str | None, name: str) -> Decimal:
        if value is None:
            return Decimal("0")
        try:
            amount = value if isinstance(value, Decimal) else Decimal(str(value))
        except Exception as exc:
            raise ValueError(f"{name} must be a valid number") from exc
        if not amount.is_finite():
            raise ValueError(f"{name} must be finite")
        return amount

    @classmethod
    def calculate_work_breakdown(
        cls,
        *,
        days_worked: Decimal | float | int | str,
        daily_wage: Decimal | float | int | str | None,
        hours_worked: Optional[Decimal | float | int | str] = None,
        wage_basis: str = "daily",
        hourly_rate: Optional[Decimal | float | int | str] = None,
        overtime_hours: Decimal | float | int | str = 0,
        overtime_multiplier: Decimal | float | int | str = "1.5",
    ) -> Dict[str, Decimal]:
        """Return base pay, overtime premium and total with explicit rate semantics.

        Daily work uses a standard 8-hour day for overtime. Legacy hourly records
        with no hourly_rate continue to derive the rate from daily_wage / 8.
        For hourly work, hours_worked includes overtime_hours.
        """
        days = cls._decimal(days_worked, "days_worked")
        hours = cls._decimal(hours_worked, "hours_worked")
        overtime = cls._decimal(overtime_hours, "overtime_hours")
        daily_rate = cls._decimal(daily_wage, "daily_wage")
        explicit_hourly_rate = cls._decimal(hourly_rate, "hourly_rate")
        multiplier = cls._decimal(overtime_multiplier, "overtime_multiplier")

        if min(days, hours, overtime, daily_rate, explicit_hourly_rate) < 0:
            raise ValueError("Work units and wage rates cannot be negative")
        if multiplier < 1 or multiplier > 3:
            raise ValueError("overtime_multiplier must be between 1 and 3")
        if overtime > 0 and hours == 0 and days == 0:
            raise ValueError("Overtime requires recorded work hours or days")

        if wage_basis == "hourly":
            if explicit_hourly_rate <= 0 or hours <= 0 or days != 0:
                raise ValueError("Hourly work requires a positive hourly rate and hours, with zero days")
            if overtime > hours:
                raise ValueError("Overtime hours cannot exceed total hours worked")
            base_rate = explicit_hourly_rate
            regular_hours = hours - overtime
            base_earned = regular_hours * base_rate
            overtime_earned = overtime * base_rate * multiplier
        elif wage_basis == "daily":
            if days > 0:
                base_earned = days * daily_rate
                base_rate = explicit_hourly_rate if explicit_hourly_rate > 0 else daily_rate / Decimal("8")
                overtime_earned = overtime * base_rate * multiplier
            elif hours > 0:
                base_rate = explicit_hourly_rate if explicit_hourly_rate > 0 else daily_rate / Decimal("8")
                if overtime > hours:
                    raise ValueError("Overtime hours cannot exceed total hours worked")
                base_earned = (hours - overtime) * base_rate
                overtime_earned = overtime * base_rate * multiplier
            else:
                base_earned = Decimal("0")
                overtime_earned = Decimal("0")
        else:
            raise ValueError("wage_basis must be 'daily' or 'hourly'")

        return {
            "base_earned": quantize_money(base_earned),
            "overtime_earned": quantize_money(overtime_earned),
            "total_earned": quantize_money(base_earned + overtime_earned),
        }


def get_wage_calculator() -> WageCalculator:
    return WageCalculator()
