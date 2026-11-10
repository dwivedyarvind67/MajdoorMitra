"""Deterministic wage trends and worker-owned savings targets."""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer, Payment, SavingsGoal, WorkEntry
from app.schemas.insights import (
    EmployerInsight,
    FinancialInsightsResponse,
    MonthlyInsight,
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
)
from app.services.audit_service import AuditService
from app.services.wage_calculator import quantize_money
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/insights", tags=["financial insights"])
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


def _month_date(year: int, month: int) -> date:
    return date(year + (month - 1) // 12, (month - 1) % 12 + 1, 1)


@router.get("", response_model=FinancialInsightsResponse)
async def get_financial_insights(
    months: int = Query(6, ge=1, le=24),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Compute wage trends only from this worker's persisted ledger values."""
    today = datetime.now(INDIA_TIMEZONE).date()
    current_month = _month_date(today.year, today.month)
    first_month = _month_date(current_month.year, current_month.month - months + 1)
    end_month = _month_date(current_month.year, current_month.month + 1)
    start_dt = datetime.combine(first_month, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_month, time.min, tzinfo=timezone.utc)

    works = list((await db.execute(
        select(WorkEntry).where(
            WorkEntry.worker_id == worker_id,
            WorkEntry.work_date >= start_dt,
            WorkEntry.work_date < end_dt,
        ).order_by(WorkEntry.work_date)
    )).scalars().all())
    payments = list((await db.execute(
        select(Payment).where(
            Payment.worker_id == worker_id,
            Payment.payment_date >= start_dt,
            Payment.payment_date < end_dt,
        ).order_by(Payment.payment_date)
    )).scalars().all())

    months_data: dict[str, dict] = {}
    for offset in range(months):
        current = _month_date(first_month.year, first_month.month + offset)
        key = current.strftime("%Y-%m")
        months_data[key] = {
            "month": key,
            "earnings": Decimal("0.00"),
            "payments": Decimal("0.00"),
            "recorded_dates": set(),
            "worked_days": Decimal("0.00"),
        }

    employers = list((await db.execute(
        select(Employer).where(Employer.worker_id == worker_id)
    )).scalars().all())
    employer_names = {employer.id: employer.name for employer in employers}
    employer_totals: dict[str | None, dict] = defaultdict(lambda: {
        "earnings": Decimal("0.00"), "payments": Decimal("0.00")
    })

    for entry in works:
        key = entry.work_date.strftime("%Y-%m")
        if key not in months_data:
            continue
        bucket = months_data[key]
        bucket["earnings"] += Decimal(str(entry.total_earned))
        bucket["recorded_dates"].add(entry.work_date.date())
        bucket["worked_days"] += Decimal(str(entry.days_worked or 0))
        employer_totals[entry.employer_id]["earnings"] += Decimal(str(entry.total_earned))
    for payment in payments:
        key = payment.payment_date.strftime("%Y-%m")
        if key not in months_data:
            continue
        months_data[key]["payments"] += Decimal(str(payment.amount))
        employer_totals[payment.employer_id]["payments"] += Decimal(str(payment.amount))

    monthly = []
    for bucket in months_data.values():
        balance = quantize_money(bucket["earnings"] - bucket["payments"])
        monthly.append(MonthlyInsight(
            month=bucket["month"],
            earnings=quantize_money(bucket["earnings"]),
            payments=quantize_money(bucket["payments"]),
            pending=max(balance, Decimal("0.00")),
            recorded_workdays=len(bucket["recorded_dates"]),
            worked_days=quantize_money(bucket["worked_days"]),
        ))

    total_earnings = quantize_money(sum((Decimal(str(row.total_earned)) for row in works), Decimal("0")))
    total_payments = quantize_money(sum((Decimal(str(row.amount)) for row in payments), Decimal("0")))
    total_pending = max(quantize_money(total_earnings - total_payments), Decimal("0.00"))
    recorded_dates = {row.work_date.date() for row in works}
    worked_days = quantize_money(sum((Decimal(str(row.days_worked or 0)) for row in works), Decimal("0")))
    daily_rate_entries = [row for row in works if row.wage_basis == "daily"]
    daily_rate_days = sum((Decimal(str(row.days_worked or 0)) for row in daily_rate_entries), Decimal("0"))
    daily_rate_earnings = sum((Decimal(str(row.total_earned)) for row in daily_rate_entries), Decimal("0"))
    average = quantize_money(daily_rate_earnings / daily_rate_days) if daily_rate_days > 0 else Decimal("0.00")
    employer_insights = []
    for employer_id, totals in employer_totals.items():
        balance = quantize_money(totals["earnings"] - totals["payments"])
        employer_insights.append(EmployerInsight(
            employer_id=employer_id,
            employer_name=employer_names.get(employer_id, "मालिक दर्ज नहीं") if employer_id else "मालिक दर्ज नहीं",
            earnings=quantize_money(totals["earnings"]),
            payments=quantize_money(totals["payments"]),
            pending=max(balance, Decimal("0.00")),
        ))
    employer_insights.sort(key=lambda item: item.earnings, reverse=True)

    return FinancialInsightsResponse(
        period_start=first_month,
        period_end=today,
        total_earnings=total_earnings,
        total_payments=total_payments,
        total_pending=total_pending,
        average_daily_earnings=average,
        recorded_workdays=len(recorded_dates),
        worked_days=worked_days,
        monthly=monthly,
        employers=employer_insights,
    )


@router.get("/savings-goals", response_model=list[SavingsGoalResponse])
async def list_savings_goals(
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavingsGoal).where(SavingsGoal.worker_id == worker_id).order_by(SavingsGoal.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/savings-goals",
    response_model=SavingsGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_savings_goal(
    body: SavingsGoalCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    goal = SavingsGoal(
        id=str(uuid.uuid4()),
        worker_id=worker_id,
        name=body.name.strip(),
        target_amount=quantize_money(body.target_amount),
        target_date=body.target_date,
        active=True,
    )
    db.add(goal)
    await db.flush()
    AuditService.record(
        db, worker_id, "savings_goal.created", "savings_goal", goal.id,
        details={"target_amount": str(goal.target_amount), "target_date": body.target_date.isoformat() if body.target_date else None},
    )
    await db.refresh(goal)
    return goal


@router.patch("/savings-goals/{goal_id}", response_model=SavingsGoalResponse)
async def update_savings_goal(
    goal_id: str,
    body: SavingsGoalUpdate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    goal = (await db.execute(
        select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.worker_id == worker_id)
    )).scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found.")
    previous = goal.active
    goal.active = body.active
    AuditService.record(
        db, worker_id, "savings_goal.updated", "savings_goal", goal.id,
        details={"active_before": previous, "active_after": body.active},
    )
    await db.flush()
    await db.refresh(goal)
    return goal


@router.delete("/savings-goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_savings_goal(
    goal_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    goal = (await db.execute(
        select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.worker_id == worker_id)
    )).scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found.")
    AuditService.record(db, worker_id, "savings_goal.deleted", "savings_goal", goal.id)
    await db.delete(goal)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
