"""Worker-scoped audit events remain atomic with ledger changes."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.models import AuditEvent, Employer, Worker
from app.schemas.ledger import PaymentCreate, WorkEntryCreate
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_financial_records_write_worker_owned_audit_events(db_session: AsyncSession):
    worker = Worker(
        id="audit-worker",
        name="Audit Worker",
        phone="9876500010",
        pin_hash="test-hash",
    )
    employer = Employer(
        id="audit-employer",
        worker_id=worker.id,
        name="Audit Employer",
    )
    db_session.add_all([worker, employer])
    await db_session.commit()

    work = await LedgerService.create_work_entry(
        db_session,
        worker.id,
        WorkEntryCreate(
            employer_id=employer.id,
            work_date="2026-11-10",
            days_worked="1.5",
            daily_wage="700.00",
        ),
    )
    payment = await LedgerService.create_payment(
        db_session,
        worker.id,
        PaymentCreate(
            employer_id=employer.id,
            payment_date="2026-11-10",
            amount="350.00",
            payment_type="advance",
        ),
    )

    events = (
        await db_session.execute(
            select(AuditEvent).where(AuditEvent.worker_id == worker.id).order_by(AuditEvent.event_type)
        )
    ).scalars().all()
    assert [(event.event_type, event.entity_id) for event in events] == [
        ("ledger.payment_recorded", payment.id),
        ("ledger.work_recorded", work.id),
    ]
    assert events[0].details["amount"] == "350.00"
    assert events[1].details["total_earned"] == "1050.00"
    assert all(event.worker_id == worker.id for event in events)


@pytest.mark.asyncio
async def test_ledger_rollback_discards_matching_audit_event(db_session: AsyncSession):
    worker = Worker(
        id="rollback-worker",
        name="Rollback Worker",
        phone="9876500011",
        pin_hash="test-hash",
    )
    db_session.add(worker)
    await db_session.commit()
    worker_id = worker.id

    await LedgerService.create_payment(
        db_session,
        worker.id,
        PaymentCreate(
            payment_date="2026-11-10",
            amount="100.00",
            payment_type="cash",
        ),
    )
    await db_session.rollback()

    events = (
        await db_session.execute(select(AuditEvent).where(AuditEvent.worker_id == worker_id))
    ).scalars().all()
    assert events == []


@pytest.mark.asyncio
async def test_audit_endpoint_returns_only_the_authenticated_workers_events(
    client: AsyncClient,
    test_worker: Worker,
    auth_token: str,
    db_session: AsyncSession,
):
    other_worker = Worker(
        id="other-audit-worker",
        name="Other Worker",
        phone="9876500012",
        pin_hash="test-hash",
    )
    db_session.add(other_worker)
    await db_session.flush()
    AuditService.record(
        db_session,
        test_worker.id,
        "voice.record_confirmed",
        "voice_statement",
        "own-statement",
        details={"status": "confirmed"},
    )
    AuditService.record(
        db_session,
        other_worker.id,
        "voice.record_confirmed",
        "voice_statement",
        "other-statement",
        details={"status": "confirmed"},
    )
    await db_session.commit()

    response = await client.get(
        "/api/ledger/audit",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["worker_id"] == test_worker.id
    assert records[0]["entity_id"] == "own-statement"
