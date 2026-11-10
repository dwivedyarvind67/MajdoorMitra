"""
Ledger Service for MazdoorMitra.
Manages database persistence for WorkEntries and Payments with strict worker isolation,
duplicate prevention, and atomic transactions.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.models import AuditEvent, WorkEntry, Payment, PaymentAllocation, Employer, VoiceStatement, StatementStatus, PaymentType
from app.schemas.ledger import WorkEntryCreate, PaymentCreate, PaymentAllocationCreate, LedgerSummary, EmployerSummary, TransactionItem
from app.services.audit_service import AuditService
from app.services.wage_calculator import WageCalculator, quantize_money


class LedgerService:
    """Handles financial transactions, ledger persistence, and worker summaries."""

    MAX_MONEY = Decimal("9999999999999.99")

    @staticmethod
    async def check_duplicate_work_entry(
        session: AsyncSession,
        worker_id: str,
        work_date: datetime,
        daily_wage: Decimal,
        days_worked: Decimal,
        employer_id: Optional[str] = None,
        hours_worked: Optional[Decimal] = None,
    ) -> bool:
        """Check for an exact same-worker, same-employer work entry."""
        stmt = select(WorkEntry).where(
            and_(
                WorkEntry.worker_id == worker_id,
                WorkEntry.work_date == work_date,
                WorkEntry.daily_wage == daily_wage,
                WorkEntry.days_worked == days_worked,
                WorkEntry.employer_id.is_(None) if employer_id is None else WorkEntry.employer_id == employer_id,
                WorkEntry.hours_worked.is_(None) if hours_worked is None else WorkEntry.hours_worked == hours_worked,
            )
        )
        res = await session.execute(stmt)
        return res.scalars().first() is not None

    @staticmethod
    async def check_duplicate_payment(
        session: AsyncSession,
        worker_id: str,
        payment_date: datetime,
        amount: Decimal,
        employer_id: Optional[str] = None,
        payment_type: Optional[PaymentType] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Check for an exact same-worker, same-employer payment."""
        stmt = select(Payment).where(
            and_(
                Payment.worker_id == worker_id,
                Payment.payment_date == payment_date,
                Payment.amount == amount,
                Payment.employer_id.is_(None) if employer_id is None else Payment.employer_id == employer_id,
                Payment.payment_type == payment_type if payment_type is not None else True,
                Payment.notes.is_(None) if notes is None else Payment.notes == notes,
            )
        )
        res = await session.execute(stmt)
        return res.scalars().first() is not None

    @classmethod
    async def create_work_entry(
        cls,
        session: AsyncSession,
        worker_id: str,
        data: WorkEntryCreate,
        source_statement_id: Optional[str] = None,
    ) -> WorkEntry:
        """Create a new work entry with deterministic calculation."""
        work_dt = datetime.combine(data.work_date, datetime.min.time(), tzinfo=timezone.utc)
        await cls._validate_employer(session, worker_id, data.employer_id)
        if source_statement_id:
            existing_source = await session.execute(
                select(WorkEntry.id).where(
                    WorkEntry.worker_id == worker_id,
                    WorkEntry.source_statement_id == source_statement_id,
                )
            )
            if existing_source.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This voice statement is already recorded.")

        if await cls.check_duplicate_work_entry(
            session, worker_id, work_dt, data.daily_wage, data.days_worked,
            employer_id=data.employer_id, hours_worked=data.hours_worked,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A work entry with identical date, wage, and days already exists.",
            )

        total_earned = WageCalculator.calculate_work_entry_total(
            days_worked=data.days_worked,
            daily_wage=data.daily_wage or Decimal("0"),
            hours_worked=data.hours_worked,
            wage_basis=data.wage_basis,
            hourly_rate=data.hourly_rate,
            overtime_hours=data.overtime_hours,
            overtime_multiplier=data.overtime_multiplier,
        )
        if total_earned > cls.MAX_MONEY:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The calculated total is above the supported range. Please check the days and wage rate.",
            )

        entry = WorkEntry(
            worker_id=worker_id,
            employer_id=data.employer_id,
            work_date=work_dt,
            days_worked=data.days_worked,
            hours_worked=data.hours_worked,
            daily_wage=data.daily_wage or Decimal("0"),
            wage_basis=data.wage_basis,
            hourly_rate=data.hourly_rate,
            overtime_hours=data.overtime_hours,
            overtime_multiplier=data.overtime_multiplier,
            total_earned=total_earned,
            description=data.description,
            source_statement_id=source_statement_id,
        )
        session.add(entry)
        await session.flush()
        AuditService.record(
            session,
            worker_id,
            "ledger.work_recorded",
            "work_entry",
            entry.id,
            source_statement_id=source_statement_id,
            details={
                "work_date": data.work_date.isoformat(),
                "employer_id": data.employer_id,
                "days_worked": str(data.days_worked),
                "hours_worked": str(data.hours_worked) if data.hours_worked is not None else None,
                "daily_wage": str(data.daily_wage) if data.daily_wage is not None else None,
                "wage_basis": data.wage_basis,
                "hourly_rate": str(data.hourly_rate) if data.hourly_rate is not None else None,
                "overtime_hours": str(data.overtime_hours),
                "overtime_multiplier": str(data.overtime_multiplier),
                "total_earned": str(total_earned),
            },
        )
        await session.flush()
        await session.refresh(entry)
        return entry

    @classmethod
    async def create_payment(
        cls,
        session: AsyncSession,
        worker_id: str,
        data: PaymentCreate,
        source_statement_id: Optional[str] = None,
    ) -> Payment:
        """Record a new payment received by the worker."""
        pay_dt = datetime.combine(data.payment_date, datetime.min.time(), tzinfo=timezone.utc)
        await cls._validate_employer(session, worker_id, data.employer_id)
        amount = quantize_money(data.amount)
        payment_type = PaymentType(data.payment_type)
        if source_statement_id:
            existing_source = await session.execute(
                select(Payment.id).where(
                    Payment.worker_id == worker_id,
                    Payment.source_statement_id == source_statement_id,
                )
            )
            if existing_source.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This voice statement is already recorded.")

        if await cls.check_duplicate_payment(
            session, worker_id, pay_dt, amount, employer_id=data.employer_id,
            payment_type=payment_type, notes=data.notes,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A payment with identical date and amount already exists.",
            )

        payment = Payment(
            worker_id=worker_id,
            employer_id=data.employer_id,
            amount=amount,
            payment_date=pay_dt,
            payment_type=payment_type,
            notes=data.notes,
            source_statement_id=source_statement_id,
        )
        session.add(payment)
        await session.flush()
        AuditService.record(
            session,
            worker_id,
            "ledger.payment_recorded",
            "payment",
            payment.id,
            source_statement_id=source_statement_id,
            details={
                "payment_date": data.payment_date.isoformat(),
                "employer_id": data.employer_id,
                "amount": str(amount),
                "payment_type": payment_type.value,
            },
        )
        await session.flush()
        await session.refresh(payment)
        return payment

    @classmethod
    async def allocate_payment(
        cls,
        session: AsyncSession,
        worker_id: str,
        payment_id: str,
        data: PaymentAllocationCreate,
    ) -> PaymentAllocation:
        """Allocate part of a payment to one work entry without changing ledger totals."""
        payment = (
            await session.execute(
                select(Payment)
                .where(Payment.id == payment_id, Payment.worker_id == worker_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found.")

        work_entry = (
            await session.execute(
                select(WorkEntry)
                .where(WorkEntry.id == data.work_entry_id, WorkEntry.worker_id == worker_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if work_entry is None:
            raise HTTPException(status_code=404, detail="Work entry not found.")
        if payment.employer_id and payment.employer_id != work_entry.employer_id:
            raise HTTPException(
                status_code=422,
                detail="Payment and work entry belong to different employers.",
            )

        payment_allocated = await session.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                PaymentAllocation.worker_id == worker_id,
                PaymentAllocation.payment_id == payment.id,
            )
        )
        work_allocated = await session.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                PaymentAllocation.worker_id == worker_id,
                PaymentAllocation.work_entry_id == work_entry.id,
            )
        )
        amount = quantize_money(data.amount)
        payment_remaining = quantize_money(payment.amount - Decimal(str(payment_allocated or 0)))
        work_remaining = quantize_money(work_entry.total_earned - Decimal(str(work_allocated or 0)))
        if amount > payment_remaining:
            raise HTTPException(
                status_code=422,
                detail=f"This payment has only Rs {payment_remaining} left to allocate.",
            )
        if amount > work_remaining:
            raise HTTPException(
                status_code=422,
                detail=f"This work entry has only Rs {work_remaining} left to allocate.",
            )

        allocation = PaymentAllocation(
            worker_id=worker_id,
            payment_id=payment.id,
            work_entry_id=work_entry.id,
            amount=amount,
        )
        session.add(allocation)
        await session.flush()
        AuditService.record(
            session,
            worker_id,
            "ledger.payment_allocated",
            "payment_allocation",
            allocation.id,
            details={
                "payment_id": payment.id,
                "work_entry_id": work_entry.id,
                "amount": str(amount),
            },
        )
        await session.flush()
        await session.refresh(allocation)
        return allocation

    @staticmethod
    async def _validate_employer(
        session: AsyncSession,
        worker_id: str,
        employer_id: Optional[str],
    ) -> None:
        if employer_id is None:
            return
        result = await session.execute(
            select(Employer.id).where(Employer.id == employer_id, Employer.worker_id == worker_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employer not found.")

    @classmethod
    async def get_summary(
        cls,
        session: AsyncSession,
        worker_id: str,
        employer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> LedgerSummary:
        """Compute full ledger summary for worker with optional filtering."""
        work_query = select(WorkEntry).where(WorkEntry.worker_id == worker_id)
        pay_query = select(Payment).where(Payment.worker_id == worker_id)

        if employer_id:
            work_query = work_query.where(WorkEntry.employer_id == employer_id)
            pay_query = pay_query.where(Payment.employer_id == employer_id)

        if start_date:
            work_query = work_query.where(WorkEntry.work_date >= start_date)
            pay_query = pay_query.where(Payment.payment_date >= start_date)

        if end_date:
            work_query = work_query.where(WorkEntry.work_date < end_date)
            pay_query = pay_query.where(Payment.payment_date < end_date)

        work_entries = (await session.execute(work_query)).scalars().all()
        payments = (await session.execute(pay_query)).scalars().all()

        calc_result = WageCalculator.calculate_summary(list(work_entries), list(payments))

        # Employer summaries
        employer_summaries = await cls.get_employer_summaries(
            session, worker_id, employer_id=employer_id, start_date=start_date, end_date=end_date
        )

        return LedgerSummary(
            total_earned=calc_result["total_earned"],
            total_received=calc_result["total_received"],
            total_advances=calc_result["total_advances"],
            balance=calc_result["balance"],
            pending=calc_result["pending"],
            overpaid=calc_result["overpaid"],
            total_work_days=calc_result["total_days_worked"],
            employer_count=len(employer_summaries),
            employers=employer_summaries,
        )

    @classmethod
    async def get_employer_summaries(
        cls,
        session: AsyncSession,
        worker_id: str,
        employer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[EmployerSummary]:
        """Get summary broken down by employer."""
        employer_query = select(Employer).where(Employer.worker_id == worker_id)
        if employer_id:
            employer_query = employer_query.where(Employer.id == employer_id)
        employers = (await session.execute(employer_query)).scalars().all()

        results = []
        for emp in employers:
            work_query = select(WorkEntry).where(
                and_(WorkEntry.worker_id == worker_id, WorkEntry.employer_id == emp.id)
            )
            pay_query = select(Payment).where(
                and_(Payment.worker_id == worker_id, Payment.employer_id == emp.id)
            )
            if start_date:
                work_query = work_query.where(WorkEntry.work_date >= start_date)
                pay_query = pay_query.where(Payment.payment_date >= start_date)
            if end_date:
                work_query = work_query.where(WorkEntry.work_date < end_date)
                pay_query = pay_query.where(Payment.payment_date < end_date)
            w_entries = (await session.execute(work_query)).scalars().all()
            p_entries = (await session.execute(pay_query)).scalars().all()

            c = WageCalculator.calculate_summary(list(w_entries), list(p_entries))
            results.append(
                EmployerSummary(
                    employer_id=emp.id,
                    employer_name=emp.name,
                    total_earned=c["total_earned"],
                    total_received=c["total_received"],
                    total_advances=c["total_advances"],
                    pending=c["pending"],
                    balance=c["balance"],
                    overpaid=c["overpaid"],
                    total_work_days=c["total_days_worked"],
                )
            )
        return results

    @classmethod
    async def get_transaction_timeline(
        cls,
        session: AsyncSession,
        worker_id: str,
        limit: int = 50,
        employer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TransactionItem]:
        """Combined timeline of work entries and payments ordered by date."""
        w_stmt = (
            select(WorkEntry)
            .where(WorkEntry.worker_id == worker_id)
        )
        p_stmt = (
            select(Payment)
            .where(Payment.worker_id == worker_id)
        )
        if employer_id:
            w_stmt = w_stmt.where(WorkEntry.employer_id == employer_id)
            p_stmt = p_stmt.where(Payment.employer_id == employer_id)
        if start_date:
            w_stmt = w_stmt.where(WorkEntry.work_date >= start_date)
            p_stmt = p_stmt.where(Payment.payment_date >= start_date)
        if end_date:
            w_stmt = w_stmt.where(WorkEntry.work_date < end_date)
            p_stmt = p_stmt.where(Payment.payment_date < end_date)
        w_stmt = w_stmt.order_by(desc(WorkEntry.work_date)).limit(limit)
        p_stmt = p_stmt.order_by(desc(Payment.payment_date)).limit(limit)

        w_list = (await session.execute(w_stmt)).scalars().all()
        p_list = (await session.execute(p_stmt)).scalars().all()

        # Fetch employers
        emp_stmt = select(Employer).where(Employer.worker_id == worker_id)
        emp_map = {e.id: e.name for e in (await session.execute(emp_stmt)).scalars().all()}

        source_ids = {item.source_statement_id for item in [*w_list, *p_list] if item.source_statement_id}
        statement_map = {}
        corrected_statement_ids = set()
        if source_ids:
            statements = (
                await session.execute(
                    select(VoiceStatement).where(
                        VoiceStatement.worker_id == worker_id,
                        VoiceStatement.id.in_(source_ids),
                    )
                )
            ).scalars().all()
            statement_map = {statement.id: statement for statement in statements}
            correction_rows = await session.execute(
                select(AuditEvent.source_statement_id).where(
                    AuditEvent.worker_id == worker_id,
                    AuditEvent.source_statement_id.in_(source_ids),
                    AuditEvent.event_type == "voice.correction_applied",
                )
            )
            corrected_statement_ids = {row[0] for row in correction_rows.all()}

        def provenance(source_statement_id: Optional[str]) -> dict:
            statement = statement_map.get(source_statement_id) if source_statement_id else None
            confirmed = bool(statement and statement.status == StatementStatus.CONFIRMED)
            return {
                "record_status": "worker_confirmed" if confirmed else "worker_reported",
                "was_corrected": bool(source_statement_id and source_statement_id in corrected_statement_ids),
                "confirmed_at": statement.confirmed_at if confirmed else None,
            }

        items: List[TransactionItem] = []
        for w in w_list:
            items.append(
                TransactionItem(
                    id=w.id,
                    type="work",
                    date=w.work_date,
                    amount=w.total_earned,
                    days_worked=w.days_worked,
                    daily_wage=w.daily_wage,
                    wage_basis=w.wage_basis,
                    hourly_rate=w.hourly_rate,
                    hours_worked=w.hours_worked,
                    overtime_hours=w.overtime_hours,
                    overtime_multiplier=w.overtime_multiplier,
                    employer_id=w.employer_id,
                    employer_name=emp_map.get(w.employer_id) if w.employer_id else None,
                    description=w.description or f"{w.days_worked} days @ Rs {w.daily_wage}",
                    source_statement_id=w.source_statement_id,
                    **provenance(w.source_statement_id),
                )
            )

        for p in p_list:
            items.append(
                TransactionItem(
                    id=p.id,
                    type="payment",
                    date=p.payment_date,
                    amount=p.amount,
                    payment_type=p.payment_type.value if hasattr(p.payment_type, "value") else str(p.payment_type),
                    employer_id=p.employer_id,
                    employer_name=emp_map.get(p.employer_id) if p.employer_id else None,
                    description=p.notes or f"Payment ({p.payment_type})",
                    source_statement_id=p.source_statement_id,
                    **provenance(p.source_statement_id),
                )
            )

        items.sort(key=lambda x: x.date, reverse=True)
        return items[:limit]
