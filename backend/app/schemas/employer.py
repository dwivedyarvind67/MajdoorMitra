from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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
