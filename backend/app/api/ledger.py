"""
Ledger API endpoints: summaries, work entries, payments, and combined timeline.
All queries are filtered by the authenticated worker_id for data isolation.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import AuditEvent, Employer, WorkEntry, Payment, PaymentAllocation
from app.schemas.ledger import (
    AuditEventResponse,
    AttendanceDay,
    LedgerSummary,
    LedgerAlertResponse,
    PaymentCreate,
    PaymentAllocationCreate,
    PaymentAllocationResponse,
    PaymentResponse,
    TransactionItem,
    TransactionList,
    WorkEntryCreate,
    WorkEntryResponse,
)
from app.services.ledger_service import LedgerService
from app.services.mismatch_service import MismatchService
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


@router.get("/alerts", response_model=List[LedgerAlertResponse])
async def get_ledger_alerts(
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Return explainable, worker-scoped ledger checks without changing records."""
    return await MismatchService.get_alerts(db, worker_id)


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
    if sd and ed and sd > ed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date must be on or before end date.")
    if ed:
        ed += timedelta(days=1)

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
    if sd and ed and sd > ed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date must be on or before end date.")
    if ed:
        ed += timedelta(days=1)

    work_query = select(WorkEntry).where(WorkEntry.worker_id == worker_id)
    if employer_id:
        work_query = work_query.where(WorkEntry.employer_id == employer_id)
    if sd:
        work_query = work_query.where(WorkEntry.work_date >= sd)
    if ed:
        work_query = work_query.where(WorkEntry.work_date < ed)

    work_query = work_query.order_by(WorkEntry.work_date.desc()).limit(limit).offset(offset)
    result = await db.execute(work_query)
    entries = result.scalars().all()

    # Build employer name map
    emp_map = await _get_employer_map(db, worker_id)
    allocated_rows = await db.execute(
        select(PaymentAllocation.work_entry_id, func.sum(PaymentAllocation.amount))
        .where(PaymentAllocation.worker_id == worker_id)
        .group_by(PaymentAllocation.work_entry_id)
    )
    allocation_map = {entry_id: amount for entry_id, amount in allocated_rows.all()}

    return [
        WorkEntryResponse(
            id=e.id,
            worker_id=e.worker_id,
            employer_id=e.employer_id,
            employer_name=emp_map.get(e.employer_id) if e.employer_id else None,
            worksite_id=e.worksite_id,
            worksite_name=e.worksite.name if e.worksite else None,
            work_date=e.work_date,
            days_worked=e.days_worked,
            hours_worked=e.hours_worked,
            daily_wage=e.daily_wage,
            wage_basis=e.wage_basis,
            hourly_rate=e.hourly_rate,
            overtime_hours=e.overtime_hours,
            overtime_multiplier=e.overtime_multiplier,
            total_earned=e.total_earned,
            allocated_amount=allocation_map.get(e.id, 0),
            outstanding_amount=max(e.total_earned - allocation_map.get(e.id, 0), 0),
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
        worksite_id=entry.worksite_id,
        worksite_name=entry.worksite.name if entry.worksite else None,
        work_date=entry.work_date,
        days_worked=entry.days_worked,
        hours_worked=entry.hours_worked,
        daily_wage=entry.daily_wage,
        wage_basis=entry.wage_basis,
        hourly_rate=entry.hourly_rate,
        overtime_hours=entry.overtime_hours,
        overtime_multiplier=entry.overtime_multiplier,
        total_earned=entry.total_earned,
        allocated_amount=0,
        outstanding_amount=entry.total_earned,
        description=entry.description,
        source_statement_id=entry.source_statement_id,
        created_at=entry.created_at,
    )


@router.put("/work/{entry_id}", response_model=WorkEntryResponse)
async def correct_work_entry(
    entry_id: str,
    body: WorkEntryCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Correct a worker-owned diary record with a fresh calculation and audit event."""
    entry = await LedgerService.update_work_entry(db, worker_id, entry_id, body)
    emp_map = await _get_employer_map(db, worker_id)
    allocated = await db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
            PaymentAllocation.worker_id == worker_id,
            PaymentAllocation.work_entry_id == entry.id,
        )
    )
    allocated_amount = Decimal(str(allocated or 0))
    return WorkEntryResponse(
        id=entry.id,
        worker_id=entry.worker_id,
        employer_id=entry.employer_id,
        employer_name=emp_map.get(entry.employer_id) if entry.employer_id else None,
        worksite_id=entry.worksite_id,
        worksite_name=entry.worksite.name if entry.worksite else None,
        work_date=entry.work_date,
        days_worked=entry.days_worked,
        hours_worked=entry.hours_worked,
        daily_wage=entry.daily_wage,
        wage_basis=entry.wage_basis,
        hourly_rate=entry.hourly_rate,
        overtime_hours=entry.overtime_hours,
        overtime_multiplier=entry.overtime_multiplier,
        total_earned=entry.total_earned,
        allocated_amount=allocated_amount,
        outstanding_amount=max(entry.total_earned - allocated_amount, Decimal("0.00")),
        description=entry.description,
        source_statement_id=entry.source_statement_id,
        created_at=entry.created_at,
    )


@router.get("/calendar", response_model=List[AttendanceDay])
async def get_attendance_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    employer_id: Optional[str] = Query(None),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Summarize actual recorded work entries for one calendar month."""
    if employer_id:
        await LedgerService._validate_employer(db, worker_id, employer_id)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
    result = await db.execute(
        select(WorkEntry).where(
            WorkEntry.worker_id == worker_id,
            WorkEntry.work_date >= start,
            WorkEntry.work_date < end,
            *([WorkEntry.employer_id == employer_id] if employer_id else []),
        ).order_by(WorkEntry.work_date)
    )
    grouped: dict = {}
    for entry in result.scalars().all():
        day = entry.work_date.date()
        totals = grouped.setdefault(day, {
            "date": day,
            "recorded_entries": 0,
            "total_days_worked": Decimal("0.00"),
            "total_hours_worked": Decimal("0.00"),
            "total_earned": Decimal("0.00"),
        })
        totals["recorded_entries"] += 1
        totals["total_days_worked"] += entry.days_worked or Decimal("0")
        totals["total_hours_worked"] += entry.hours_worked or Decimal("0")
        totals["total_earned"] += entry.total_earned or Decimal("0")
    return [AttendanceDay(**grouped[day]) for day in sorted(grouped)]


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
    if sd and ed and sd > ed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date must be on or before end date.")
    if ed:
        ed += timedelta(days=1)

    pay_query = select(Payment).where(Payment.worker_id == worker_id)
    if employer_id:
        pay_query = pay_query.where(Payment.employer_id == employer_id)
    if sd:
        pay_query = pay_query.where(Payment.payment_date >= sd)
    if ed:
        pay_query = pay_query.where(Payment.payment_date < ed)

    pay_query = pay_query.order_by(Payment.payment_date.desc()).limit(limit).offset(offset)
    result = await db.execute(pay_query)
    payments = result.scalars().all()

    emp_map = await _get_employer_map(db, worker_id)
    allocated_rows = await db.execute(
        select(PaymentAllocation.payment_id, func.sum(PaymentAllocation.amount))
        .where(PaymentAllocation.worker_id == worker_id)
        .group_by(PaymentAllocation.payment_id)
    )
    allocation_map = {payment_id: amount for payment_id, amount in allocated_rows.all()}

    return [
        PaymentResponse(
            id=p.id,
            worker_id=p.worker_id,
            employer_id=p.employer_id,
            employer_name=emp_map.get(p.employer_id) if p.employer_id else None,
            amount=p.amount,
            allocated_amount=allocation_map.get(p.id, 0),
            unallocated_amount=max(p.amount - allocation_map.get(p.id, 0), 0),
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
        allocated_amount=0,
        unallocated_amount=payment.amount,
        payment_date=payment.payment_date,
        payment_type=payment.payment_type.value if hasattr(payment.payment_type, "value") else str(payment.payment_type),
        notes=payment.notes,
        source_statement_id=payment.source_statement_id,
        created_at=payment.created_at,
    )


@router.get("/transactions", response_model=TransactionList)
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    employer_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Combined timeline with optional employer and inclusive date filters."""
    sd = _parse_date(start_date) if start_date else None
    ed = _parse_date(end_date) if end_date else None
    if sd and ed and sd > ed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date must be on or before end date.")
    if ed:
        ed += timedelta(days=1)
    items = await LedgerService.get_transaction_timeline(
        db, worker_id, limit=limit, employer_id=employer_id, start_date=sd, end_date=ed
    )
    return TransactionList(transactions=items, total_count=len(items))


@router.post(
    "/payments/{payment_id}/allocations",
    response_model=PaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def allocate_payment(
    payment_id: str,
    body: PaymentAllocationCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Apply part of a payment or advance to one recorded work entry."""
    return await LedgerService.allocate_payment(db, worker_id, payment_id, body)


@router.get("/audit", response_model=List[AuditEventResponse])
async def list_audit_events(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List immutable change events for the authenticated worker only."""
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.worker_id == worker_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


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
