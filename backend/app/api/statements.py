"""
Statement history endpoints and PDF download.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import VoiceStatement, Worker, Employer, WorkEntry, Payment
from app.schemas.statement import StatementDetail, StatementListItem
from app.services.pdf_service import PDFService, get_pdf_service
from app.services.wage_calculator import WageCalculator
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/statements", tags=["statements"])


@router.get("", response_model=List[StatementListItem])
async def list_statements(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List voice statements for the authenticated worker."""
    result = await db.execute(
        select(VoiceStatement)
        .where(VoiceStatement.worker_id == worker_id)
        .order_by(VoiceStatement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


def _date_bound(value: str | None, *, next_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD format.") from exc
    if next_day:
        parsed += timedelta(days=1)
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


@router.get("/export")
async def export_ledger_statement(
    start_date: Optional[str] = Query(None, description="Inclusive start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="Inclusive end date in YYYY-MM-DD format"),
    employer_id: Optional[str] = Query(None),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Export an authenticated worker's exact ledger slice as a bilingual PDF."""
    start = _date_bound(start_date)
    end = _date_bound(end_date, next_day=True)
    if start and end and start >= end:
        raise HTTPException(status_code=400, detail="Start date must be on or before end date.")

    employer_name = None
    if employer_id:
        employer_result = await db.execute(
            select(Employer).where(Employer.id == employer_id, Employer.worker_id == worker_id)
        )
        employer = employer_result.scalar_one_or_none()
        if employer is None:
            raise HTTPException(status_code=404, detail="Employer not found.")
        employer_name = employer.name

    work_query = select(WorkEntry).where(WorkEntry.worker_id == worker_id)
    payment_query = select(Payment).where(Payment.worker_id == worker_id)
    if employer_id:
        work_query = work_query.where(WorkEntry.employer_id == employer_id)
        payment_query = payment_query.where(Payment.employer_id == employer_id)
    if start:
        work_query = work_query.where(WorkEntry.work_date >= start)
        payment_query = payment_query.where(Payment.payment_date >= start)
    if end:
        work_query = work_query.where(WorkEntry.work_date < end)
        payment_query = payment_query.where(Payment.payment_date < end)
    works = list((await db.execute(work_query.order_by(WorkEntry.work_date.desc()))).scalars().all())
    payments = list((await db.execute(payment_query.order_by(Payment.payment_date.desc()))).scalars().all())

    worker = (await db.execute(select(Worker).where(Worker.id == worker_id))).scalar_one_or_none()
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found.")

    source_ids = {
        row.source_statement_id for row in [*works, *payments] if row.source_statement_id
    }
    status_map = {}
    if source_ids:
        source_rows = (await db.execute(
            select(VoiceStatement.id, VoiceStatement.status).where(
                VoiceStatement.worker_id == worker_id,
                VoiceStatement.id.in_(source_ids),
            )
        )).all()
        status_map = {statement_id: statement_status.value for statement_id, statement_status in source_rows}

    def provenance(source_id: str | None) -> str:
        return "worker confirmed" if source_id and status_map.get(source_id) == "CONFIRMED" else "worker reported"

    work_dicts = [{
        "work_date": row.work_date,
        "days_worked": row.days_worked,
        "hours_worked": row.hours_worked,
        "wage_basis": row.wage_basis,
        "daily_wage": row.daily_wage,
        "hourly_rate": row.hourly_rate,
        "overtime_hours": row.overtime_hours,
        "overtime_multiplier": row.overtime_multiplier,
        "total_earned": row.total_earned,
        "description": row.description,
        "record_status": provenance(row.source_statement_id),
    } for row in works]
    payment_dicts = [{
        "payment_date": row.payment_date,
        "amount": row.amount,
        "payment_type": row.payment_type.value if hasattr(row.payment_type, "value") else str(row.payment_type),
        "notes": row.notes,
        "record_status": provenance(row.source_statement_id),
    } for row in payments]
    summary = WageCalculator.calculate_summary(works, payments)
    transaction_dates = [row.work_date for row in works] + [row.payment_date for row in payments]
    period_start = start or min(transaction_dates, default=None)
    period_end = (end - timedelta(days=1)) if end else max(transaction_dates, default=None)
    pdf_bytes = get_pdf_service().generate_statement(
        worker_name=worker.name,
        worker_phone=worker.phone,
        employer_name=employer_name,
        period_start=period_start,
        period_end=period_end,
        work_entries=work_dicts,
        payments=payment_dicts,
        summary=summary,
        confirmation_status="Ledger export; entries are individually labelled as reported or worker-confirmed.",
    )
    suffix = f"{start_date or 'all'}_{end_date or 'all'}"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="wage_statement_{suffix}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{statement_id}", response_model=StatementDetail)
async def get_statement(
    statement_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific voice statement."""
    result = await db.execute(
        select(VoiceStatement).where(
            VoiceStatement.id == statement_id,
            VoiceStatement.worker_id == worker_id,
        )
    )
    stmt = result.scalar_one_or_none()
    if not stmt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Statement not found.",
        )
    return stmt


@router.get("/{statement_id}/pdf")
async def download_pdf(
    statement_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Download a PDF wage statement."""
    statement_result = await db.execute(
        select(VoiceStatement).where(
            VoiceStatement.id == statement_id,
            VoiceStatement.worker_id == worker_id,
        )
    )
    statement = statement_result.scalar_one_or_none()
    if statement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found.")
    if statement.status.value != "CONFIRMED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only worker-confirmed statements can be downloaded.")

    # Get worker info
    worker_result = await db.execute(
        select(Worker).where(Worker.id == worker_id)
    )
    worker = worker_result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")

    # Include only the records created from this confirmed statement. This keeps
    # the confirmation label tied to the actual source instead of the whole ledger.
    work_result = await db.execute(
        select(WorkEntry).where(
            WorkEntry.worker_id == worker_id,
            WorkEntry.source_statement_id == statement.id,
        ).order_by(WorkEntry.work_date.desc())
    )
    work_entries = work_result.scalars().all()

    pay_result = await db.execute(
        select(Payment).where(
            Payment.worker_id == worker_id,
            Payment.source_statement_id == statement.id,
        ).order_by(Payment.payment_date.desc())
    )
    payments = pay_result.scalars().all()

    # Calculate summary
    summary = WageCalculator.calculate_summary(list(work_entries), list(payments))

    # Convert to dicts for PDF
    work_dicts = [
        {
            "work_date": e.work_date,
            "days_worked": e.days_worked,
            "hours_worked": e.hours_worked,
            "wage_basis": e.wage_basis,
            "daily_wage": e.daily_wage,
            "hourly_rate": e.hourly_rate,
            "overtime_hours": e.overtime_hours,
            "overtime_multiplier": e.overtime_multiplier,
            "total_earned": e.total_earned,
            "description": e.description,
            "record_status": "worker confirmed",
        }
        for e in work_entries
    ]
    pay_dicts = [
        {
            "payment_date": p.payment_date,
            "amount": p.amount,
            "payment_type": p.payment_type.value if hasattr(p.payment_type, "value") else str(p.payment_type),
            "notes": p.notes,
            "record_status": "worker confirmed",
        }
        for p in payments
    ]

    # Determine period
    transaction_dates = [e.work_date for e in work_entries] + [p.payment_date for p in payments]
    period_start = min(transaction_dates, default=None)
    period_end = max(transaction_dates, default=None)

    pdf_svc = get_pdf_service()
    pdf_bytes = pdf_svc.generate_statement(
        worker_name=worker.name,
        worker_phone=worker.phone,
        employer_name=None,  # Overall statement, not employer-specific
        period_start=period_start,
        period_end=period_end,
        work_entries=work_dicts,
        payments=pay_dicts,
        summary=summary,
        transcript=statement.transcript,
        confirmation_status=statement.status.value,
        confirmed_at=statement.confirmed_at,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="wage_statement_{statement_id[:8]}.pdf"'
        },
    )
