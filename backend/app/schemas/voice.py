from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class StatementStatus(str, Enum):
    INITIAL = "INITIAL"
    TRANSCRIBED = "TRANSCRIBED"
    EXTRACTED = "EXTRACTED"
    AWAITING_INFORMATION = "AWAITING_INFORMATION"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class VoiceSessionCreate(BaseModel):
    language: str = Field(default="hi", pattern=r'^(hi|en)$')


class VoiceSessionResponse(BaseModel):
    id: str
    status: StatementStatus
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    id: str
    transcript: str
    status: StatementStatus


class ExtractionResult(BaseModel):
    intent: Optional[str] = None
    days_worked: Optional[Decimal] = None
    daily_wage: Optional[Decimal] = None
    hours_worked: Optional[Decimal] = None
    wage_basis: Literal["daily", "hourly"] = "daily"
    hourly_rate: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = Decimal("0.00")
    overtime_multiplier: Optional[Decimal] = Decimal("1.50")
    base_earned: Optional[Decimal] = None
    overtime_earned: Optional[Decimal] = None
    calculated_total: Optional[Decimal] = None
    possible_duplicates: List[dict[str, Any]] = Field(default_factory=list)
    work_date: Optional[str] = None
    amount_received: Optional[Decimal] = None
    payment_type: Optional[str] = None
    employer_name: Optional[str] = None
    description: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    requires_confirmation: bool = True


class ExtractionResponse(BaseModel):
    id: str
    status: StatementStatus
    extracted_data: Optional[ExtractionResult] = None
    question: Optional[str] = None
    conversation_history: Optional[List[dict]] = None


class ReplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


class ReplyResponse(BaseModel):
    id: str
    status: StatementStatus
    extracted_data: Optional[ExtractionResult] = None
    question: Optional[str] = None
    transcript: Optional[str] = None


class ExtractionCorrection(BaseModel):
    """Worker-entered corrections applied before explicit confirmation."""

    intent: Optional[str] = Field(None, pattern=r"^(log_work|log_payment)$")
    days_worked: Optional[Decimal] = Field(None, ge=0, le=31, max_digits=15, decimal_places=2)
    daily_wage: Optional[Decimal] = Field(None, ge=0, max_digits=15, decimal_places=2)
    hours_worked: Optional[Decimal] = Field(None, ge=0, le=24, max_digits=15, decimal_places=2)
    wage_basis: Optional[Literal["daily", "hourly"]] = None
    hourly_rate: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    overtime_hours: Optional[Decimal] = Field(None, ge=0, le=24, max_digits=15, decimal_places=2)
    overtime_multiplier: Optional[Decimal] = Field(None, ge=1, le=3, max_digits=4, decimal_places=2)
    work_date: Optional[date] = None
    amount_received: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    payment_type: Optional[str] = Field(None, pattern=r"^(cash|upi|bank|advance|other)$")
    employer_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class CorrectionRequest(BaseModel):
    corrections: ExtractionCorrection


class ConfirmResponse(BaseModel):
    id: str
    status: StatementStatus
    work_entry_id: Optional[str] = None
    payment_id: Optional[str] = None
    message: str


class SpeakRequest(BaseModel):
    text: Optional[str] = None  # If None, auto-generate summary


class SpeakResponse(BaseModel):
    audio_url: Optional[str] = None
    text: str
    audio_base64: Optional[str] = None
    audio_content_type: Optional[str] = None
