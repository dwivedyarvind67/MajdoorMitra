"""
Employer management endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer
from app.schemas.employer import EmployerCreate, EmployerResponse
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/employers", tags=["employers"])


@router.get("", response_model=List[EmployerResponse])
async def list_employers(
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List all employers for the authenticated worker."""
    result = await db.execute(
        select(Employer)
        .where(Employer.worker_id == worker_id)
        .order_by(Employer.name)
    )
    return result.scalars().all()


@router.post("", response_model=EmployerResponse, status_code=status.HTTP_201_CREATED)
async def create_employer(
    body: EmployerCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a new employer for the authenticated worker."""
    # Check for duplicate name
    existing = await db.execute(
        select(Employer).where(
            Employer.worker_id == worker_id,
            Employer.name == body.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employer '{body.name}' already exists.",
        )

    employer = Employer(
        id=str(uuid.uuid4()),
        worker_id=worker_id,
        name=body.name,
        contact_details=body.contact_details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(employer)
    await db.commit()
    await db.refresh(employer)
    return employer
