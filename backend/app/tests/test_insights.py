"""Financial insights are reproducible from the worker's persisted ledger."""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_monthly_insights_use_exact_ledger_records(client: AsyncClient, auth_token, test_employer):
    headers = {"Authorization": f"Bearer {auth_token}"}
    work = await client.post(
        "/api/ledger/work", headers=headers,
        json={"employer_id": test_employer.id, "work_date": date.today().isoformat(), "days_worked": "6", "daily_wage": "700"},
    )
    payment = await client.post(
        "/api/ledger/payments", headers=headers,
        json={"employer_id": test_employer.id, "payment_date": date.today().isoformat(), "amount": "3000", "payment_type": "cash"},
    )
    assert work.status_code == 201 and payment.status_code == 201

    response = await client.get("/api/insights?months=1", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert Decimal(data["total_earnings"]) == Decimal("4200.00")
    assert Decimal(data["total_payments"]) == Decimal("3000.00")
    assert Decimal(data["total_pending"]) == Decimal("1200.00")
    assert Decimal(data["average_daily_earnings"]) == Decimal("700.00")
    assert data["recorded_workdays"] == 1
    assert Decimal(data["worked_days"]) == Decimal("6.00")
    assert data["monthly"][0]["month"] == date.today().strftime("%Y-%m")
    assert data["employers"][0]["employer_name"] == test_employer.name


@pytest.mark.asyncio
async def test_savings_goals_are_worker_scoped_and_audited(client: AsyncClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    created = await client.post(
        "/api/insights/savings-goals", headers=headers,
        json={"name": "बच्चों की पढ़ाई", "target_amount": "25000.00", "target_date": "2027-06-01"},
    )
    assert created.status_code == 201, created.text
    goal = created.json()
    assert goal["target_amount"] == "25000.00"

    listed = await client.get("/api/insights/savings-goals", headers=headers)
    assert [item["id"] for item in listed.json()] == [goal["id"]]

    from app.utils.auth import create_access_token
    other_token = create_access_token({"sub": "00000000-0000-0000-0000-000000000001"})
    forbidden_owner = {"Authorization": f"Bearer {other_token}"}
    assert (await client.patch(f"/api/insights/savings-goals/{goal['id']}", headers=forbidden_owner, json={"active": False})).status_code == 404

    updated = await client.patch(
        f"/api/insights/savings-goals/{goal['id']}", headers=headers, json={"active": False}
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False
    deleted = await client.delete(f"/api/insights/savings-goals/{goal['id']}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/api/insights/savings-goals", headers=headers)).json() == []
