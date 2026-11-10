from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class EmployerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact_details: Optional[str] = Field(None, max_length=200)


class EmployerResponse(BaseModel):
    id: str
    worker_id: str
    name: str
    contact_details: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorksiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)


class WorksiteResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: Optional[str] = None
    name: str
    address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WageAgreementCreate(BaseModel):
    worksite_id: Optional[str] = Field(None, min_length=1, max_length=36)
    wage_basis: Literal["daily", "hourly"]
    daily_rate: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    hourly_rate: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    overtime_multiplier: Decimal = Field(Decimal("1.5"), ge=1, le=3, max_digits=4, decimal_places=2)
    effective_from: date
    effective_to: Optional[date] = None
    terms: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_rate_and_period(self):
        if self.wage_basis == "daily" and (self.daily_rate is None or self.hourly_rate is not None):
            raise ValueError("Daily agreements require a daily rate and no hourly rate.")
        if self.wage_basis == "hourly" and (self.hourly_rate is None or self.daily_rate is not None):
            raise ValueError("Hourly agreements require an hourly rate and no daily rate.")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("The agreement end date must be on or after its start date.")
        return self


class WageAgreementResponse(BaseModel):
    id: str
    worker_id: str
    employer_id: str
    worksite_id: Optional[str] = None
    wage_basis: str
    daily_rate: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    overtime_multiplier: Decimal
    effective_from: date
    effective_to: Optional[date] = None
    terms: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
