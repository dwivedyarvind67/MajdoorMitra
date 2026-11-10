from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: str
    worker_id: str
    file_name: Optional[str] = None
    document_type: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    consent_given: bool
    statement_id: Optional[str] = None
    work_entry_id: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


EvidenceKind = Literal[
    "payment_receipt", "wage_agreement", "work_document", "audio", "other"
]
