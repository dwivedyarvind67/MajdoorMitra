from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class StatementListItem(BaseModel):
    id: str
    transcript: Optional[str] = None
    language: str
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StatementDetail(BaseModel):
    id: str
    worker_id: str
    transcript: Optional[str] = None
    language: str
    extracted_data: Optional[dict] = None
    status: str
    conversation_history: Optional[List[dict]] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
