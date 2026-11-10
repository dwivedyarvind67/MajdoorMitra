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
from app.models.models import Employer, WageAgreement, Worksite
from app.schemas.employer import (
    EmployerCreate,
    EmployerResponse,
    WageAgreementCreate,
    WageAgreementResponse,
    WorksiteCreate,
    WorksiteResponse,
)
from app.services.audit_service import AuditService
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
    await db.flush()
    AuditService.record(
        db,
        worker_id,
        "employer.created",
        "employer",
        employer.id,
        details={"name": employer.name},
    )
    await db.commit()
    await db.refresh(employer)
    return employer


async def _get_worker_employer(db: AsyncSession, worker_id: str, employer_id: str) -> Employer:
    result = await db.execute(
        select(Employer).where(Employer.id == employer_id, Employer.worker_id == worker_id)
    )
    employer = result.scalar_one_or_none()
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found.")
    return employer


@router.get("/{employer_id}/worksites", response_model=List[WorksiteResponse])
async def list_worksites(
    employer_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List sites associated with one of the authenticated worker's employers."""
    await _get_worker_employer(db, worker_id, employer_id)
    result = await db.execute(
        select(Worksite)
        .where(Worksite.worker_id == worker_id, Worksite.employer_id == employer_id)
        .order_by(Worksite.name)
    )
    return result.scalars().all()


@router.post(
    "/{employer_id}/worksites",
    response_model=WorksiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_worksite(
    employer_id: str,
    body: WorksiteCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a worksite for an employer owned by the authenticated worker."""
    await _get_worker_employer(db, worker_id, employer_id)
    worksite = Worksite(
        id=str(uuid.uuid4()),
        worker_id=worker_id,
        employer_id=employer_id,
        name=body.name.strip(),
        address=body.address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(worksite)
    await db.flush()
    AuditService.record(
        db, worker_id, "worksite.created", "worksite", worksite.id,
        details={"employer_id": employer_id, "name": worksite.name},
    )
    await db.refresh(worksite)
    return worksite


@router.get("/{employer_id}/agreements", response_model=List[WageAgreementResponse])
async def list_wage_agreements(
    employer_id: str,
    worksite_id: str | None = None,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List wage terms for this employer, optionally narrowed to one site."""
    await _get_worker_employer(db, worker_id, employer_id)
    stmt = select(WageAgreement).where(
        WageAgreement.worker_id == worker_id,
        WageAgreement.employer_id == employer_id,
    )
    if worksite_id:
        stmt = stmt.where(WageAgreement.worksite_id == worksite_id)
    result = await db.execute(stmt.order_by(WageAgreement.effective_from.desc()))
    return result.scalars().all()


@router.post(
    "/{employer_id}/agreements",
    response_model=WageAgreementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wage_agreement(
    employer_id: str,
    body: WageAgreementCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Save reported wage terms for an employer and effective period."""
    await _get_worker_employer(db, worker_id, employer_id)
    if body.worksite_id:
        result = await db.execute(
            select(Worksite).where(
                Worksite.id == body.worksite_id,
                Worksite.worker_id == worker_id,
                Worksite.employer_id == employer_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Worksite not found for this employer.")

    agreement = WageAgreement(
        id=str(uuid.uuid4()),
        worker_id=worker_id,
        employer_id=employer_id,
        worksite_id=body.worksite_id,
        wage_basis=body.wage_basis,
        daily_rate=body.daily_rate,
        hourly_rate=body.hourly_rate,
        overtime_multiplier=body.overtime_multiplier,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        terms=body.terms,
        created_at=datetime.now(timezone.utc),
    )
    db.add(agreement)
    await db.flush()
    AuditService.record(
        db, worker_id, "wage_agreement.created", "wage_agreement", agreement.id,
        details={
            "employer_id": employer_id,
            "worksite_id": body.worksite_id,
            "wage_basis": body.wage_basis,
            "effective_from": body.effective_from.isoformat(),
            "effective_to": body.effective_to.isoformat() if body.effective_to else None,
        },
    )
    await db.refresh(agreement)
    return agreement
