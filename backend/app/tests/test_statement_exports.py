"""Period-specific ledger exports are worker-scoped and use ledger totals."""

from decimal import Decimal

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_period_employer_export_contains_only_matching_records_and_exact_totals(
    client: AsyncClient, auth_token, test_employer, monkeypatch
):
    from app.api import statements

    headers = {"Authorization": f"Bearer {auth_token}"}
    work_early = await client.post(
        "/api/ledger/work", headers=headers,
        json={"employer_id": test_employer.id, "work_date": "2026-11-10", "days_worked": "2", "daily_wage": "700"},
    )
    work_late = await client.post(
        "/api/ledger/work", headers=headers,
        json={"employer_id": test_employer.id, "work_date": "2026-11-20", "days_worked": "1", "daily_wage": "500"},
    )
    payment = await client.post(
        "/api/ledger/payments", headers=headers,
        json={"employer_id": test_employer.id, "payment_date": "2026-11-12", "amount": "300", "payment_type": "cash"},
    )
    assert work_early.status_code == 201 and work_late.status_code == 201 and payment.status_code == 201

    captured = {}

    class CapturingPdf:
        def generate_statement(self, **kwargs):
            captured.update(kwargs)
            return b"%PDF-1.4 test"

    monkeypatch.setattr(statements, "get_pdf_service", lambda: CapturingPdf())
    response = await client.get(
        f"/api/statements/export?start_date=2026-11-01&end_date=2026-11-15&employer_id={test_employer.id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert captured["employer_name"] == test_employer.name
    assert len(captured["work_entries"]) == 1
    assert len(captured["payments"]) == 1
    assert captured["work_entries"][0]["record_status"] == "worker reported"
    assert Decimal(captured["summary"]["total_earned"]) == Decimal("1400.00")
    assert Decimal(captured["summary"]["total_received"]) == Decimal("300.00")
    assert Decimal(captured["summary"]["pending"]) == Decimal("1100.00")


@pytest.mark.asyncio
async def test_export_rejects_invalid_ranges_and_employer_from_another_worker(
    client: AsyncClient, auth_token
):
    headers = {"Authorization": f"Bearer {auth_token}"}
    invalid_range = await client.get(
        "/api/statements/export?start_date=2026-11-20&end_date=2026-11-10", headers=headers
    )
    assert invalid_range.status_code == 400
    missing_employer = await client.get(
        "/api/statements/export?employer_id=not-owned", headers=headers
    )
    assert missing_employer.status_code == 404
