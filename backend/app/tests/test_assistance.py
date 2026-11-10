"""Worker assistance drafts are based on records and never send messages."""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_request_draft_uses_indian_grouping_and_does_not_send(
    client: AsyncClient, auth_token, test_employer
):
    headers = {"Authorization": f"Bearer {auth_token}"}
    work = await client.post(
        "/api/ledger/work", headers=headers,
        json={"employer_id": test_employer.id, "work_date": date.today().isoformat(), "days_worked": "31", "daily_wage": "7000"},
    )
    payment = await client.post(
        "/api/ledger/payments", headers=headers,
        json={"employer_id": test_employer.id, "payment_date": date.today().isoformat(), "amount": "92000", "payment_type": "upi"},
    )
    assert work.status_code == 201 and payment.status_code == 201

    response = await client.get(
        f"/api/assistance/payment-request?employer_id={test_employer.id}&language=hi", headers=headers
    )
    assert response.status_code == 200
    draft = response.json()
    assert Decimal(draft["amount_in_recorded_balance"]) == Decimal("125000.00")
    assert "1,25,000.00" in draft["message"]
    assert draft["delivery"] == "copy_only"


@pytest.mark.asyncio
async def test_official_resources_and_zero_balance_draft(client: AsyncClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resources = await client.get("/api/assistance/resources", headers=headers)
    assert resources.status_code == 200
    assert any(resource["url"] == "https://www.eshram.gov.in/helpdesk" for resource in resources.json())

    faqs = await client.get("/api/assistance/faqs", headers=headers)
    assert faqs.status_code == 200
    assert "not legal advice" in faqs.json()["disclaimer"].lower()

    no_balance = await client.get("/api/assistance/payment-request", headers=headers)
    assert no_balance.status_code == 409
