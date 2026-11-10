"""
Tests for LedgerService and financial duplicate prevention.
"""

import pytest
from httpx import AsyncClient
from datetime import date, datetime, timezone
from decimal import Decimal
from app.schemas.ledger import WorkEntryCreate, PaymentCreate, PaymentAllocationCreate
from app.services.ledger_service import LedgerService
from app.models.models import Worker, Employer, PaymentAllocation, AuditEvent, VoiceStatement, StatementStatus
from sqlalchemy import select


@pytest.mark.asyncio
async def test_duplicate_prevention_work_entry(db_session):
    worker = Worker(
        id="worker-test-1",
        name="Test Worker",
        phone="9876543211",
        pin_hash="dummy",
    )
    db_session.add(worker)
    await db_session.commit()

    entry_data = WorkEntryCreate(
        work_date=date(2026, 11, 10),
        days_worked=Decimal("1.0"),
        daily_wage=Decimal("700.00"),
        description="Plaster work",
    )

    # First entry succeeds
    entry1 = await LedgerService.create_work_entry(db_session, worker.id, entry_data)
    assert entry1.id is not None

    # Duplicate entry should raise HTTPException 409
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await LedgerService.create_work_entry(db_session, worker.id, entry_data)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_prevention_payment(db_session):
    worker = Worker(
        id="worker-test-2",
        name="Test Worker 2",
        phone="9876543212",
        pin_hash="dummy",
    )
    db_session.add(worker)
    await db_session.commit()

    pay_data = PaymentCreate(
        payment_date=date(2026, 11, 10),
        amount=Decimal("1500.00"),
        payment_type="cash",
    )

    # First payment succeeds
    pay1 = await LedgerService.create_payment(db_session, worker.id, pay_data)
    assert pay1.id is not None

    # Duplicate payment raises 409
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await LedgerService.create_payment(db_session, worker.id, pay_data)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_partial_advance_allocation_is_capped_and_does_not_double_count(db_session):
    worker = Worker(
        id="allocation-worker", name="Allocation Worker", phone="9876543230", pin_hash="dummy"
    )
    employer = Employer(id="allocation-employer", worker_id=worker.id, name="Builder")
    db_session.add_all([worker, employer])
    await db_session.commit()

    work = await LedgerService.create_work_entry(
        db_session,
        worker.id,
        WorkEntryCreate(
            employer_id=employer.id,
            work_date=date(2026, 11, 10),
            days_worked=Decimal("1"),
            daily_wage=Decimal("700"),
        ),
    )
    advance = await LedgerService.create_payment(
        db_session,
        worker.id,
        PaymentCreate(
            employer_id=employer.id,
            payment_date=date(2026, 11, 10),
            amount=Decimal("500"),
            payment_type="advance",
        ),
    )

    allocation = await LedgerService.allocate_payment(
        db_session,
        worker.id,
        advance.id,
        PaymentAllocationCreate(work_entry_id=work.id, amount=Decimal("300")),
    )
    assert allocation.amount == Decimal("300.00")

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await LedgerService.allocate_payment(
            db_session,
            worker.id,
            advance.id,
            PaymentAllocationCreate(work_entry_id=work.id, amount=Decimal("250")),
        )
    assert exc_info.value.status_code == 422

    totals = await LedgerService.get_summary(db_session, worker.id, employer_id=employer.id)
    assert totals.total_earned == Decimal("700.00")
    assert totals.total_received == Decimal("500.00")
    assert totals.total_advances == Decimal("500.00")
    assert totals.balance == Decimal("200.00")
    saved_allocations = (
        await db_session.execute(
            select(PaymentAllocation).where(PaymentAllocation.worker_id == worker.id)
        )
    ).scalars().all()
    assert [row.amount for row in saved_allocations] == [Decimal("300.00")]
    events = (
        await db_session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "ledger.payment_allocated")
        )
    ).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_hourly_overtime_work_entry_calculation_is_stored(db_session):
    worker = Worker(
        id="hourly-worker", name="Hourly Worker", phone="9876543231", pin_hash="dummy"
    )
    db_session.add(worker)
    await db_session.commit()

    entry = await LedgerService.create_work_entry(
        db_session,
        worker.id,
        WorkEntryCreate(
            work_date=date(2026, 11, 10),
            days_worked=Decimal("0"),
            wage_basis="hourly",
            hourly_rate=Decimal("100"),
            hours_worked=Decimal("10"),
            overtime_hours=Decimal("2"),
        ),
    )
    assert entry.total_earned == Decimal("1100.00")
    assert entry.wage_basis == "hourly"
    assert entry.hourly_rate == Decimal("100.00")


@pytest.mark.asyncio
async def test_payment_allocation_api_returns_worker_scoped_remaining_amounts(
    client: AsyncClient, db_session, test_worker, test_employer, auth_token
):
    work = await LedgerService.create_work_entry(
        db_session,
        test_worker.id,
        WorkEntryCreate(
            employer_id=test_employer.id,
            work_date=date(2026, 11, 10),
            days_worked=Decimal("1"),
            daily_wage=Decimal("700"),
        ),
    )
    payment = await LedgerService.create_payment(
        db_session,
        test_worker.id,
        PaymentCreate(
            employer_id=test_employer.id,
            payment_date=date(2026, 11, 10),
            amount=Decimal("500"),
            payment_type="advance",
        ),
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    before = (await client.get("/api/ledger/payments", headers=headers)).json()[0]
    assert before["unallocated_amount"] == "500.00"

    allocated = await client.post(
        f"/api/ledger/payments/{payment.id}/allocations",
        json={"work_entry_id": work.id, "amount": "200.00"},
        headers=headers,
    )
    assert allocated.status_code == 201
    assert allocated.json()["amount"] == "200.00"

    after_payment = (await client.get("/api/ledger/payments", headers=headers)).json()[0]
    after_work = (await client.get("/api/ledger/work", headers=headers)).json()[0]
    assert after_payment["allocated_amount"] == "200.00"
    assert after_payment["unallocated_amount"] == "300.00"
    assert after_work["outstanding_amount"] == "500.00"

    from app.utils.auth import create_access_token
    foreign = await client.post(
        f"/api/ledger/payments/{payment.id}/allocations",
        json={"work_entry_id": work.id, "amount": "100.00"},
        headers={"Authorization": f"Bearer {create_access_token({'sub': 'foreign-worker'})}"},
    )
    assert foreign.status_code == 404


@pytest.mark.asyncio
async def test_wage_story_filters_dates_and_labels_confirmation_and_corrections(
    client: AsyncClient, db_session, test_worker, test_employer, auth_token
):
    statement = VoiceStatement(
        id="confirmed-story-statement",
        worker_id=test_worker.id,
        language="hi",
        status=StatementStatus.CONFIRMED,
        transcript="मैंने एक दिन काम किया",
        confirmed_at=datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc),
    )
    db_session.add(statement)
    await db_session.commit()
    voice_work = await LedgerService.create_work_entry(
        db_session,
        test_worker.id,
        WorkEntryCreate(
            employer_id=test_employer.id,
            work_date=date(2026, 11, 10),
            days_worked=Decimal("1"),
            daily_wage=Decimal("700"),
        ),
        source_statement_id=statement.id,
    )
    db_session.add(AuditEvent(
        worker_id=test_worker.id,
        event_type="voice.correction_applied",
        entity_type="voice_statement",
        entity_id=statement.id,
        source_statement_id=statement.id,
        details={"fields": ["daily_wage"]},
    ))
    await LedgerService.create_work_entry(
        db_session,
        test_worker.id,
        WorkEntryCreate(
            employer_id=test_employer.id,
            work_date=date(2026, 11, 9),
            days_worked=Decimal("1"),
            daily_wage=Decimal("650"),
        ),
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get(
        "/api/ledger/transactions",
        params={
            "start_date": "2026-11-10",
            "end_date": "2026-11-10",
            "employer_id": test_employer.id,
        },
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()["transactions"]
    assert [row["id"] for row in rows] == [voice_work.id]
    assert rows[0]["record_status"] == "worker_confirmed"
    assert rows[0]["was_corrected"] is True
    assert rows[0]["confirmed_at"] is not None
    daily_summary = await client.get(
        "/api/ledger/summary",
        params={"start_date": "2026-11-10", "end_date": "2026-11-10", "employer_id": test_employer.id},
        headers=headers,
    )
    assert daily_summary.status_code == 200
    assert daily_summary.json()["total_earned"] == "700.00"
    daily_work = await client.get(
        "/api/ledger/work",
        params={"start_date": "2026-11-10", "end_date": "2026-11-10", "employer_id": test_employer.id},
        headers=headers,
    )
    assert [entry["id"] for entry in daily_work.json()] == [voice_work.id]

    invalid_range = await client.get(
        "/api/ledger/transactions",
        params={"start_date": "2026-11-11", "end_date": "2026-11-10"},
        headers=headers,
    )
    assert invalid_range.status_code == 400


@pytest.mark.asyncio
async def test_mismatch_alerts_explain_sources_without_mutating_ledger(
    client: AsyncClient, db_session, test_worker, test_employer, auth_token
):
    first_work = await LedgerService.create_work_entry(
        db_session,
        test_worker.id,
        WorkEntryCreate(
            employer_id=test_employer.id,
            work_date=date(2026, 11, 10),
            days_worked=Decimal("1"),
            daily_wage=Decimal("700"),
        ),
    )
    second_work = await LedgerService.create_work_entry(
        db_session,
        test_worker.id,
        WorkEntryCreate(
            employer_id=test_employer.id,
            work_date=date(2026, 11, 11),
            days_worked=Decimal("1"),
            daily_wage=Decimal("800"),
        ),
    )
    payment = await LedgerService.create_payment(
        db_session,
        test_worker.id,
        PaymentCreate(
            employer_id=test_employer.id,
            payment_date=date(2026, 11, 12),
            amount=Decimal("200"),
            payment_type="advance",
        ),
    )
    before = await LedgerService.get_summary(db_session, test_worker.id)

    response = await client.get(
        "/api/ledger/alerts",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    alerts = response.json()
    alert_types = {alert["alert_type"] for alert in alerts}
    assert {"recorded_balance", "unallocated_payment", "rate_change"} <= alert_types

    pending_alert = next(alert for alert in alerts if alert["alert_type"] == "recorded_balance")
    assert pending_alert["amount"] == "1300.00"
    assert set(pending_alert["source_record_ids"]) == {first_work.id, second_work.id}
    payment_alert = next(alert for alert in alerts if alert["alert_type"] == "unallocated_payment")
    assert payment_alert["amount"] == "200.00"
    assert payment_alert["source_record_ids"] == [payment.id]
    assert payment_alert["source_records"][0]["record_type"] == "payment"
    assert "नहीं जोड़ा" in payment_alert["explanation"]

    after = await LedgerService.get_summary(db_session, test_worker.id)
    assert after.total_earned == before.total_earned
    assert after.total_received == before.total_received
