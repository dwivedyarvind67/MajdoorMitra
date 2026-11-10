from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class WorkEntryCreate(BaseModel):
    employer_id: Optional[str] = None
    work_date: date
    days_worked: Decimal = Field(..., ge=0, le=31, decimal_places=2)
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=24, decimal_places=2)
    daily_wage: Decimal = Field(..., ge=0, decimal_places=2)
    description: Optional[str] = Field(None, max_length=500)


class WorkEntryResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    work_date: datetime
    days_worked: Decimal
    hours_worked: Optional[Decimal] = None
    daily_wage: Decimal
    total_earned: Decimal
    description: Optional[str] = None
    source_statement_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    employer_id: Optional[str] = None
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    payment_date: date
    payment_type: str = Field(..., pattern=r'^(cash|upi|bank|advance|other)$')
    notes: Optional[str] = Field(None, max_length=500)


class PaymentResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    amount: Decimal
    payment_date: datetime
    payment_type: str
    notes: Optional[str] = None
    source_statement_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployerSummary(BaseModel):
    employer_id: str
    employer_name: str
    total_earned: Decimal
    total_received: Decimal
    total_advances: Decimal = Decimal("0.00")
    balance: Decimal
    pending: Decimal
    overpaid: Decimal = Decimal("0.00")
    total_work_days: Decimal = Decimal("0.00")


class LedgerSummary(BaseModel):
    total_earned: Decimal
    total_received: Decimal
    total_advances: Decimal
    balance: Decimal       # earned - received (positive = owed to worker)
    pending: Decimal       # max(balance, 0)
    overpaid: Decimal      # max(-balance, 0)
    total_work_days: Decimal
    employer_count: int
    employers: Optional[List[EmployerSummary]] = None


class TransactionItem(BaseModel):
    id: str
    type: str  # "work" or "payment"
    date: datetime
    amount: Decimal
    days_worked: Optional[Decimal] = None
    daily_wage: Optional[Decimal] = None
    payment_type: Optional[str] = None
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    description: Optional[str] = None
    source_statement_id: Optional[str] = None


class TransactionList(BaseModel):
    transactions: List[TransactionItem]
    total_count: int
