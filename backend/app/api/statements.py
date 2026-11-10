"""
Statement history endpoints and PDF download.
"""

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

    # Get all work entries and payments
    work_result = await db.execute(
        select(WorkEntry).where(WorkEntry.worker_id == worker_id).order_by(WorkEntry.work_date.desc())
    )
    work_entries = work_result.scalars().all()

    pay_result = await db.execute(
        select(Payment).where(Payment.worker_id == worker_id).order_by(Payment.payment_date.desc())
    )
    payments = pay_result.scalars().all()

    # Calculate summary
    summary = WageCalculator.calculate_summary(list(work_entries), list(payments))

    # Convert to dicts for PDF
    work_dicts = [
        {
            "work_date": e.work_date,
            "days_worked": e.days_worked,
            "daily_wage": e.daily_wage,
            "total_earned": e.total_earned,
            "description": e.description,
        }
        for e in work_entries
    ]
    pay_dicts = [
        {
            "payment_date": p.payment_date,
            "amount": p.amount,
            "payment_type": p.payment_type.value if hasattr(p.payment_type, "value") else str(p.payment_type),
            "notes": p.notes,
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
