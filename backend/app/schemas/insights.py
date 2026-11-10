from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MonthlyInsight(BaseModel):
    month: str
    earnings: Decimal
    payments: Decimal
    pending: Decimal
    recorded_workdays: int
    worked_days: Decimal


class EmployerInsight(BaseModel):
    employer_id: Optional[str] = None
    employer_name: str
    earnings: Decimal
    payments: Decimal
    pending: Decimal


class FinancialInsightsResponse(BaseModel):
    period_start: date
    period_end: date
    total_earnings: Decimal
    total_payments: Decimal
    total_pending: Decimal
    average_daily_earnings: Decimal
    recorded_workdays: int
    worked_days: Decimal
    monthly: list[MonthlyInsight]
    employers: list[EmployerInsight]


class SavingsGoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    target_amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    target_date: Optional[date] = None


class SavingsGoalUpdate(BaseModel):
    active: bool


class SavingsGoalResponse(BaseModel):
    id: str
    worker_id: str
    name: str
    target_amount: Decimal
    target_date: Optional[date] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
