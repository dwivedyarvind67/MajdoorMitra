"""
Comprehensive tests for WageCalculator.
All calculations must use Decimal — never float.
At least 15 test cases with explicit expected values.
"""

import pytest
from decimal import Decimal
from app.services.wage_calculator import FinancialService, WageCalculator, quantize_money, ZERO


class TestCalculateWorkEntryTotal:
    """Tests for single work entry total calculation."""

    def test_basic_daily_wage(self):
        """5 days * 500/day = 2500.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("5"), daily_wage=Decimal("500")
        )
        assert result == Decimal("2500.00")
        assert isinstance(result, Decimal)

    def test_partial_day(self):
        """0.5 days * 600/day = 300.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("0.5"), daily_wage=Decimal("600")
        )
        assert result == Decimal("300.00")

    def test_fractional_wage(self):
        """3 days * 433.33/day = 1299.99"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("3"), daily_wage=Decimal("433.33")
        )
        assert result == Decimal("1299.99")

    def test_zero_days(self):
        """0 days * 500/day = 0.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("0"), daily_wage=Decimal("500")
        )
        assert result == Decimal("0.00")

    def test_zero_wage(self):
        """5 days * 0/day = 0.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("5"), daily_wage=Decimal("0")
        )
        assert result == Decimal("0.00")

    def test_hours_based_when_zero_days(self):
        """0 days, 4 hours at 800/day => 800/8*4 = 400.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("0"),
            daily_wage=Decimal("800"),
            hours_worked=Decimal("4"),
        )
        assert result == Decimal("400.00")

    def test_large_amounts(self):
        """30 days * 1500/day = 45000.00"""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("30"), daily_wage=Decimal("1500")
        )
        assert result == Decimal("45000.00")

    def test_string_inputs(self):
        """Accept string numeric inputs, convert to Decimal."""
        result = WageCalculator.calculate_work_entry_total(
            days_worked="7", daily_wage="450"
        )
        assert result == Decimal("3150.00")
        assert isinstance(result, Decimal)

    def test_rounding_half_up(self):
        """Test that rounding follows ROUND_HALF_UP."""
        result = WageCalculator.calculate_work_entry_total(
            days_worked=Decimal("3"), daily_wage=Decimal("333.335")
        )
        # 3 * 333.335 = 1000.005 -> rounds to 1000.01
        assert result == Decimal("1000.01")


class TestCalculateTotalEarned:
    """Tests for summing total earned across multiple work entries."""

    def test_multiple_entries(self):
        """Sum of multiple work entries."""
        entries = [
            {"total_earned": Decimal("2500.00")},
            {"total_earned": Decimal("3000.00")},
            {"total_earned": Decimal("1500.00")},
        ]
        result = WageCalculator.calculate_total_earned(entries)
        assert result == Decimal("7000.00")

    def test_empty_entries(self):
        """No entries = 0."""
        result = WageCalculator.calculate_total_earned([])
        assert result == Decimal("0.00")

    def test_with_different_rates(self):
        """Entries with different daily rates, pre-computed totals."""
        entries = [
            {"days_worked": Decimal("5"), "daily_wage": Decimal("500"), "total_earned": Decimal("2500.00")},
            {"days_worked": Decimal("3"), "daily_wage": Decimal("700"), "total_earned": Decimal("2100.00")},
            {"days_worked": Decimal("2"), "daily_wage": Decimal("600"), "total_earned": Decimal("1200.00")},
        ]
        result = WageCalculator.calculate_total_earned(entries)
        assert result == Decimal("5800.00")

    def test_calculates_from_days_wage_if_no_total(self):
        """If total_earned is missing, compute from days*wage."""
        entries = [
            {"days_worked": Decimal("4"), "daily_wage": Decimal("500")},
        ]
        result = WageCalculator.calculate_total_earned(entries)
        assert result == Decimal("2000.00")


class TestCalculateTotalReceived:
    """Tests for summing payments received."""

    def test_total_with_all_types(self):
        """Sum of cash + UPI + advance = total received."""
        payments = [
            {"amount": Decimal("1000.00"), "payment_type": "cash"},
            {"amount": Decimal("2000.00"), "payment_type": "upi"},
            {"amount": Decimal("500.00"), "payment_type": "advance"},
        ]
        result = WageCalculator.calculate_total_received(payments)
        assert result == Decimal("3500.00")

    def test_exclude_advances(self):
        """When include_advances=False, advance payments are excluded."""
        payments = [
            {"amount": Decimal("1000.00"), "payment_type": "cash"},
            {"amount": Decimal("500.00"), "payment_type": "advance"},
        ]
        result = WageCalculator.calculate_total_received(payments, include_advances=False)
        assert result == Decimal("1000.00")

    def test_empty_payments(self):
        result = WageCalculator.calculate_total_received([])
        assert result == Decimal("0.00")


class TestCalculateAdvances:
    """Tests for advance-only totals."""

    def test_advances_only(self):
        payments = [
            {"amount": Decimal("500.00"), "payment_type": "advance"},
            {"amount": Decimal("1000.00"), "payment_type": "cash"},
            {"amount": Decimal("300.00"), "payment_type": "advance"},
        ]
        result = WageCalculator.calculate_total_advances(payments)
        assert result == Decimal("800.00")

    def test_no_advances(self):
        payments = [
            {"amount": Decimal("1000.00"), "payment_type": "cash"},
        ]
        result = WageCalculator.calculate_total_advances(payments)
        assert result == Decimal("0.00")


class TestBalance:
    """Tests for balance, pending, and overpaid calculations."""

    def test_positive_balance(self):
        """Worker is owed money: earned > received."""
        balance = WageCalculator.calculate_balance(
            Decimal("5000.00"), Decimal("3000.00")
        )
        assert balance == Decimal("2000.00")

    def test_zero_balance(self):
        """Fully paid."""
        balance = WageCalculator.calculate_balance(
            Decimal("5000.00"), Decimal("5000.00")
        )
        assert balance == Decimal("0.00")

    def test_negative_balance_overpaid(self):
        """Worker was overpaid: received > earned."""
        balance = WageCalculator.calculate_balance(
            Decimal("3000.00"), Decimal("5000.00")
        )
        assert balance == Decimal("-2000.00")

    def test_pending_positive(self):
        """Pending = max(balance, 0) when balance > 0."""
        assert WageCalculator.calculate_pending(Decimal("1500.00")) == Decimal("1500.00")

    def test_pending_zero_when_overpaid(self):
        """Pending = 0 when overpaid."""
        assert WageCalculator.calculate_pending(Decimal("-500.00")) == Decimal("0.00")

    def test_overpaid_positive(self):
        """Overpaid = max(-balance, 0)."""
        assert WageCalculator.calculate_overpaid(Decimal("-2000.00")) == Decimal("2000.00")

    def test_overpaid_zero_when_owed(self):
        """Overpaid = 0 when worker is owed money."""
        assert WageCalculator.calculate_overpaid(Decimal("3000.00")) == Decimal("0.00")


class TestFullSummary:
    """Tests for the complete summary calculation."""

    def test_full_scenario(self):
        """
        Worker did 10 days @ 500/day = 5000.
        Received 3000 cash + 500 advance = 3500.
        Balance = 1500, Pending = 1500, Overpaid = 0.
        """
        work_entries = [
            {"total_earned": Decimal("5000.00"), "days_worked": Decimal("10")},
        ]
        payments = [
            {"amount": Decimal("3000.00"), "payment_type": "cash"},
            {"amount": Decimal("500.00"), "payment_type": "advance"},
        ]
        summary = WageCalculator.calculate_summary(work_entries, payments)

        assert summary["total_earned"] == Decimal("5000.00")
        assert summary["total_received"] == Decimal("3500.00")
        assert summary["total_advances"] == Decimal("500.00")
        assert summary["balance"] == Decimal("1500.00")
        assert summary["pending"] == Decimal("1500.00")
        assert summary["overpaid"] == Decimal("0.00")
        assert summary["total_days_worked"] == Decimal("10.00")

    def test_overpaid_scenario(self):
        """
        Earned 2000, received 3000.
        Balance = -1000, Pending = 0, Overpaid = 1000.
        """
        work_entries = [
            {"total_earned": Decimal("2000.00"), "days_worked": Decimal("4")},
        ]
        payments = [
            {"amount": Decimal("3000.00"), "payment_type": "cash"},
        ]
        summary = WageCalculator.calculate_summary(work_entries, payments)

        assert summary["total_earned"] == Decimal("2000.00")
        assert summary["total_received"] == Decimal("3000.00")
        assert summary["balance"] == Decimal("-1000.00")
        assert summary["pending"] == Decimal("0.00")
        assert summary["overpaid"] == Decimal("1000.00")

    def test_zero_everything(self):
        """No work, no payments."""
        summary = WageCalculator.calculate_summary([], [])
        assert summary["total_earned"] == Decimal("0.00")
        assert summary["total_received"] == Decimal("0.00")
        assert summary["balance"] == Decimal("0.00")
        assert summary["pending"] == Decimal("0.00")
        assert summary["overpaid"] == Decimal("0.00")

    def test_large_amounts(self):
        """
        365 days at 1500/day = 547500.
        Received 500000. Balance = 47500.
        """
        work_entries = [
            {"total_earned": Decimal("547500.00"), "days_worked": Decimal("365")},
        ]
        payments = [
            {"amount": Decimal("500000.00"), "payment_type": "bank"},
        ]
        summary = WageCalculator.calculate_summary(work_entries, payments)

        assert summary["total_earned"] == Decimal("547500.00")
        assert summary["total_received"] == Decimal("500000.00")
        assert summary["balance"] == Decimal("47500.00")
        assert summary["pending"] == Decimal("47500.00")

    def test_decimal_precision_no_float_drift(self):
        """Ensure no floating-point drift for 0.1 + 0.2."""
        entries = [
            {"total_earned": Decimal("0.10"), "days_worked": Decimal("1")},
            {"total_earned": Decimal("0.20"), "days_worked": Decimal("1")},
        ]
        total = WageCalculator.calculate_total_earned(entries)
        assert total == Decimal("0.30")
        # Float would give 0.30000000000000004


class TestQuantizeMoney:
    """Tests for the quantize_money helper."""

    def test_from_string(self):
        assert quantize_money("123.456") == Decimal("123.46")

    def test_from_int(self):
        assert quantize_money(100) == Decimal("100.00")

    def test_already_decimal(self):
        assert quantize_money(Decimal("99.99")) == Decimal("99.99")


class TestExplicitWageBreakdown:
    def test_hourly_regular_and_overtime(self):
        result = FinancialService.calculate_work_breakdown(
            days_worked=0,
            daily_wage=None,
            wage_basis="hourly",
            hourly_rate="100",
            hours_worked="10",
            overtime_hours="2",
            overtime_multiplier="1.5",
        )
        assert result == {
            "base_earned": Decimal("800.00"),
            "overtime_earned": Decimal("300.00"),
            "total_earned": Decimal("1100.00"),
        }

    def test_daily_wage_and_overtime_premium(self):
        result = FinancialService.calculate_work_breakdown(
            days_worked="1",
            daily_wage="800",
            overtime_hours="2",
            overtime_multiplier="1.5",
        )
        assert result["base_earned"] == Decimal("800.00")
        assert result["overtime_earned"] == Decimal("300.00")
        assert result["total_earned"] == Decimal("1100.00")

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"days_worked": -1, "daily_wage": 800},
            {"days_worked": 0, "daily_wage": 800, "hours_worked": 3, "overtime_hours": 4},
            {"days_worked": 1, "daily_wage": 800, "overtime_multiplier": "0.5"},
            {"days_worked": 0, "daily_wage": None, "wage_basis": "hourly", "hours_worked": 2},
        ],
    )
    def test_invalid_wage_inputs_are_rejected(self, kwargs):
        defaults = {"days_worked": 0, "daily_wage": 800}
        defaults.update(kwargs)
        with pytest.raises(ValueError):
            FinancialService.calculate_work_breakdown(**defaults)
