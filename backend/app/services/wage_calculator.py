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
    ) -> Decimal:
        """
        Calculate total earned for a single work entry.
        Normally: days_worked * daily_wage.
        If days_worked is 0 and hours_worked is provided, calculate hourly based on standard 8-hour day.
        """
        days = Decimal(str(days_worked)) if days_worked is not None else Decimal("0")
        wage = Decimal(str(daily_wage)) if daily_wage is not None else Decimal("0")

        if days > 0:
            total = days * wage
        elif hours_worked is not None and Decimal(str(hours_worked)) > 0:
            hours = Decimal(str(hours_worked))
            hourly_rate = wage / Decimal("8")
            total = hours * hourly_rate
        else:
            total = Decimal("0")

        return quantize_money(total)

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


def get_wage_calculator() -> WageCalculator:
    return WageCalculator()
