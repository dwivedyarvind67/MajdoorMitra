"""
Ledger API endpoints: summaries, work entries, payments, and combined timeline.
All queries are filtered by the authenticated worker_id for data isolation.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer, WorkEntry, Payment
from app.schemas.ledger import (
    LedgerSummary,
    PaymentCreate,
    PaymentResponse,
    TransactionItem,
    TransactionList,
    WorkEntryCreate,
    WorkEntryResponse,
)
from app.services.ledger_service import LedgerService
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.get("/summary", response_model=LedgerSummary)
async def get_summary(
    employer_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary for the authenticated worker."""
    sd = _parse_date(start_date) if start_date else None
    ed = _parse_date(end_date) if end_date else None

    return await LedgerService.get_summary(
        db, worker_id, employer_id=employer_id, start_date=sd, end_date=ed
    )


@router.get("/work", response_model=List[WorkEntryResponse])
async def list_work_entries(
    employer_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List work entries for the authenticated worker."""
    sd = _parse_date(start_date) if start_date else None
    ed = _parse_date(end_date) if end_date else None

    work_query = select(WorkEntry).where(WorkEntry.worker_id == worker_id)
    if employer_id:
        work_query = work_query.where(WorkEntry.employer_id == employer_id)
    if sd:
        work_query = work_query.where(WorkEntry.work_date >= sd)
    if ed:
        work_query = work_query.where(WorkEntry.work_date <= ed)

    work_query = work_query.order_by(WorkEntry.work_date.desc()).limit(limit).offset(offset)
    result = await db.execute(work_query)
    entries = result.scalars().all()

    # Build employer name map
    emp_map = await _get_employer_map(db, worker_id)

    return [
        WorkEntryResponse(
            id=e.id,
            worker_id=e.worker_id,
            employer_id=e.employer_id,
            employer_name=emp_map.get(e.employer_id) if e.employer_id else None,
            work_date=e.work_date,
            days_worked=e.days_worked,
            hours_worked=e.hours_worked,
            daily_wage=e.daily_wage,
            total_earned=e.total_earned,
            description=e.description,
            source_statement_id=e.source_statement_id,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.post("/work", response_model=WorkEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_work_entry(
    body: WorkEntryCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a work entry."""
    entry = await LedgerService.create_work_entry(db, worker_id, body)
    emp_map = await _get_employer_map(db, worker_id)

    return WorkEntryResponse(
        id=entry.id,
        worker_id=entry.worker_id,
        employer_id=entry.employer_id,
        employer_name=emp_map.get(entry.employer_id) if entry.employer_id else None,
        work_date=entry.work_date,
        days_worked=entry.days_worked,
        hours_worked=entry.hours_worked,
        daily_wage=entry.daily_wage,
        total_earned=entry.total_earned,
        description=entry.description,
        source_statement_id=entry.source_statement_id,
        created_at=entry.created_at,
    )


@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    employer_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List payments for the authenticated worker."""
    sd = _parse_date(start_date) if start_date else None
    ed = _parse_date(end_date) if end_date else None

    pay_query = select(Payment).where(Payment.worker_id == worker_id)
    if employer_id:
        pay_query = pay_query.where(Payment.employer_id == employer_id)
    if sd:
        pay_query = pay_query.where(Payment.payment_date >= sd)
    if ed:
        pay_query = pay_query.where(Payment.payment_date <= ed)

    pay_query = pay_query.order_by(Payment.payment_date.desc()).limit(limit).offset(offset)
    result = await db.execute(pay_query)
    payments = result.scalars().all()

    emp_map = await _get_employer_map(db, worker_id)

    return [
        PaymentResponse(
            id=p.id,
            worker_id=p.worker_id,
            employer_id=p.employer_id,
            employer_name=emp_map.get(p.employer_id) if p.employer_id else None,
            amount=p.amount,
            payment_date=p.payment_date,
            payment_type=p.payment_type.value if hasattr(p.payment_type, "value") else str(p.payment_type),
            notes=p.notes,
            source_statement_id=p.source_statement_id,
            created_at=p.created_at,
        )
        for p in payments
    ]


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a payment."""
    payment = await LedgerService.create_payment(db, worker_id, body)
    emp_map = await _get_employer_map(db, worker_id)

    return PaymentResponse(
        id=payment.id,
        worker_id=payment.worker_id,
        employer_id=payment.employer_id,
        employer_name=emp_map.get(payment.employer_id) if payment.employer_id else None,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_type=payment.payment_type.value if hasattr(payment.payment_type, "value") else str(payment.payment_type),
        notes=payment.notes,
        source_statement_id=payment.source_statement_id,
        created_at=payment.created_at,
    )


@router.get("/transactions", response_model=TransactionList)
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Combined timeline of work entries and payments."""
    items = await LedgerService.get_transaction_timeline(db, worker_id, limit=limit)
    return TransactionList(transactions=items, total_count=len(items))


# ---- Helpers ----

def _parse_date(date_str: str) -> datetime:
    """Parse ISO date string to datetime."""
    try:
        from datetime import date as date_type
        d = date_type.fromisoformat(date_str)
        return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD.",
        )


async def _get_employer_map(db: AsyncSession, worker_id: str) -> dict:
    """Build {employer_id: employer_name} map for a worker."""
    result = await db.execute(
        select(Employer).where(Employer.worker_id == worker_id)
    )
    return {e.id: e.name for e in result.scalars().all()}
