from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any, Literal
from datetime import datetime, date
from decimal import Decimal


class WorkEntryCreate(BaseModel):
    employer_id: Optional[str] = None
    worksite_id: Optional[str] = Field(None, min_length=1, max_length=36)
    work_date: date
    days_worked: Decimal = Field(..., ge=0, le=31, max_digits=15, decimal_places=2)
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=24, max_digits=15, decimal_places=2)
    daily_wage: Optional[Decimal] = Field(None, ge=0, max_digits=15, decimal_places=2)
    wage_basis: Literal["daily", "hourly"] = "daily"
    hourly_rate: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    overtime_hours: Decimal = Field(Decimal("0"), ge=0, le=24, max_digits=15, decimal_places=2)
    overtime_multiplier: Decimal = Field(Decimal("1.5"), ge=1, le=3, max_digits=4, decimal_places=2)
    description: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_work_units(self):
        if self.wage_basis == "hourly":
            if self.hourly_rate is None:
                raise ValueError("An hourly wage rate is required for hourly work.")
            if self.days_worked != 0:
                raise ValueError("Set days_worked to 0 for hourly work.")
            if self.hours_worked is None or self.hours_worked <= 0:
                raise ValueError("Enter the total hours worked for hourly work.")
            if self.overtime_hours > self.hours_worked:
                raise ValueError("Overtime hours cannot exceed total hours worked.")
        else:
            if self.daily_wage is None:
                raise ValueError("A daily wage rate is required for daily work.")
            if self.days_worked == 0 and (self.hours_worked is None or self.hours_worked == 0):
                raise ValueError("Enter days worked or hours worked.")
        return self


class WorkEntryResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    worksite_id: Optional[str] = None
    worksite_name: Optional[str] = None
    work_date: datetime
    days_worked: Decimal
    hours_worked: Optional[Decimal] = None
    daily_wage: Decimal
    wage_basis: str = "daily"
    hourly_rate: Optional[Decimal] = None
    overtime_hours: Decimal = Decimal("0.00")
    overtime_multiplier: Decimal = Decimal("1.50")
    total_earned: Decimal
    allocated_amount: Decimal = Decimal("0.00")
    outstanding_amount: Decimal = Decimal("0.00")
    description: Optional[str] = None
    source_statement_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceDay(BaseModel):
    date: date
    recorded_entries: int
    total_days_worked: Decimal
    total_hours_worked: Decimal
    total_earned: Decimal


class PaymentCreate(BaseModel):
    employer_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    payment_date: date
    payment_type: str = Field(..., pattern=r'^(cash|upi|bank|advance|other)$')
    notes: Optional[str] = Field(None, max_length=500)


class PaymentResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    amount: Decimal
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")
    payment_date: datetime
    payment_type: str
    notes: Optional[str] = None
    source_statement_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentAllocationCreate(BaseModel):
    work_entry_id: str = Field(..., min_length=1, max_length=36)
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)


class PaymentAllocationResponse(BaseModel):
    id: str
    worker_id: str
    payment_id: str
    work_entry_id: str
    amount: Decimal
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
    wage_basis: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    hours_worked: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = None
    overtime_multiplier: Optional[Decimal] = None
    payment_type: Optional[str] = None
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    worksite_id: Optional[str] = None
    worksite_name: Optional[str] = None
    description: Optional[str] = None
    source_statement_id: Optional[str] = None
    record_status: Literal["worker_reported", "worker_confirmed"] = "worker_reported"
    was_corrected: bool = False
    confirmed_at: Optional[datetime] = None


class TransactionList(BaseModel):
    transactions: List[TransactionItem]
    total_count: int


class LedgerAlertSource(BaseModel):
    id: str
    record_type: Literal["work", "payment"]
    date: datetime
    amount: Decimal
    description: Optional[str] = None


class LedgerAlertResponse(BaseModel):
    id: str
    alert_type: Literal[
        "recorded_balance", "unallocated_payment", "possible_duplicate", "rate_change", "possible_overpayment"
    ]
    severity: Literal["review", "information"]
    employer_id: Optional[str] = None
    employer_name: Optional[str] = None
    amount: Optional[Decimal] = None
    source_record_ids: List[str]
    source_records: List[LedgerAlertSource] = Field(default_factory=list)
    explanation: str
    recommendation: str


class AuditEventResponse(BaseModel):
    id: str
    worker_id: str
    event_type: str
    entity_type: str
    entity_id: str
    source_statement_id: Optional[str] = None
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
