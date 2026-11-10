from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel


class AssistanceResource(BaseModel):
    id: str
    title: str
    description: str
    url: str
    source: str
    phone: Optional[str] = None
    availability: Optional[str] = None


class PaymentRequestDraft(BaseModel):
    employer_id: Optional[str] = None
    employer_name: str
    amount_in_recorded_balance: Decimal
    language: Literal["hi", "en"]
    message: str
    delivery: Literal["copy_only"] = "copy_only"
