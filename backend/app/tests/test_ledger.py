"""
Tests for LedgerService and financial duplicate prevention.
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from app.schemas.ledger import WorkEntryCreate, PaymentCreate
from app.services.ledger_service import LedgerService
from app.models.models import Worker, Employer


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
