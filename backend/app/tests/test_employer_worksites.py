"""Worker-scoped employer sites and dated wage agreement endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_worksite_agreement_and_work_record_flow(client: AsyncClient, auth_token, test_employer):
    headers = {"Authorization": f"Bearer {auth_token}"}
    employer_id = test_employer.id

    site_response = await client.post(
        f"/api/employers/{employer_id}/worksites",
        headers=headers,
        json={"name": "Sector 18 site", "address": "Noida"},
    )
    assert site_response.status_code == 201, site_response.text
    site = site_response.json()
    assert site["employer_id"] == employer_id

    sites_response = await client.get(f"/api/employers/{employer_id}/worksites", headers=headers)
    assert sites_response.status_code == 200
    assert [row["id"] for row in sites_response.json()] == [site["id"]]

    agreement_response = await client.post(
        f"/api/employers/{employer_id}/agreements",
        headers=headers,
        json={
            "worksite_id": site["id"],
            "wage_basis": "daily",
            "daily_rate": "750.00",
            "effective_from": "2026-11-01",
            "terms": "Worker reported rate",
        },
    )
    assert agreement_response.status_code == 201, agreement_response.text
    agreement = agreement_response.json()
    assert agreement["daily_rate"] == "750.00"
    assert agreement["worksite_id"] == site["id"]

    list_response = await client.get(
        f"/api/employers/{employer_id}/agreements?worksite_id={site['id']}", headers=headers
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    work_response = await client.post(
        "/api/ledger/work",
        headers=headers,
        json={
            "employer_id": employer_id,
            "worksite_id": site["id"],
            "work_date": "2026-11-10",
            "days_worked": "2",
            "daily_wage": "750",
        },
    )
    assert work_response.status_code == 201, work_response.text
    assert work_response.json()["worksite_id"] == site["id"]
    assert work_response.json()["worksite_name"] == "Sector 18 site"
    assert work_response.json()["total_earned"] == "1500.00"


@pytest.mark.asyncio
async def test_site_and_agreement_endpoints_enforce_worker_and_employer_scope(
    client: AsyncClient, auth_token, test_employer
):
    headers = {"Authorization": f"Bearer {auth_token}"}
    foreign_employer = await client.get("/api/employers", headers=headers)
    assert foreign_employer.status_code == 200

    missing = await client.get("/api/employers/not-owned/worksites", headers=headers)
    assert missing.status_code == 404

    invalid_agreement = await client.post(
        f"/api/employers/{test_employer.id}/agreements",
        headers=headers,
        json={
            "wage_basis": "daily",
            "hourly_rate": "100",
            "effective_from": "2026-11-01",
        },
    )
    assert invalid_agreement.status_code == 422


@pytest.mark.asyncio
async def test_work_record_rejects_worksite_from_different_employer(
    client: AsyncClient, auth_token, test_employer
):
    headers = {"Authorization": f"Bearer {auth_token}"}
    second_employer_response = await client.post(
        "/api/employers", headers=headers, json={"name": "Other Contractor"}
    )
    assert second_employer_response.status_code == 201
    second_employer_id = second_employer_response.json()["id"]

    site_response = await client.post(
        f"/api/employers/{second_employer_id}/worksites",
        headers=headers,
        json={"name": "Different employer site"},
    )
    assert site_response.status_code == 201

    work_response = await client.post(
        "/api/ledger/work",
        headers=headers,
        json={
            "employer_id": test_employer.id,
            "worksite_id": site_response.json()["id"],
            "work_date": "2026-11-10",
            "days_worked": "1",
            "daily_wage": "700",
        },
    )
    assert work_response.status_code == 422
    assert "different employer" in work_response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_diary_calendar_and_correction_record_audit(client: AsyncClient, auth_token, test_employer):
    headers = {"Authorization": f"Bearer {auth_token}"}
    create_response = await client.post(
        "/api/ledger/work",
        headers=headers,
        json={
            "employer_id": test_employer.id,
            "work_date": "2026-11-10",
            "days_worked": "1",
            "daily_wage": "700",
        },
    )
    assert create_response.status_code == 201, create_response.text
    entry_id = create_response.json()["id"]

    calendar_response = await client.get(
        "/api/ledger/calendar?year=2026&month=11", headers=headers
    )
    assert calendar_response.status_code == 200
    assert calendar_response.json() == [{
        "date": "2026-11-10",
        "recorded_entries": 1,
        "total_days_worked": "1.00",
        "total_hours_worked": "0.00",
        "total_earned": "700.00",
    }]

    correction = await client.put(
        f"/api/ledger/work/{entry_id}",
        headers=headers,
        json={
            "employer_id": test_employer.id,
            "work_date": "2026-11-10",
            "days_worked": "1.5",
            "daily_wage": "900",
        },
    )
    assert correction.status_code == 200, correction.text
    assert correction.json()["total_earned"] == "1350.00"

    audit_response = await client.get("/api/ledger/audit", headers=headers)
    assert audit_response.status_code == 200
    correction_events = [event for event in audit_response.json() if event["event_type"] == "ledger.work_corrected"]
    assert len(correction_events) == 1
    assert correction_events[0]["details"]["before"]["total_earned"] == "700.00"
    assert correction_events[0]["details"]["after"]["total_earned"] == "1350.00"

    timeline = await client.get("/api/ledger/transactions", headers=headers)
    assert timeline.status_code == 200
    corrected_entry = next(item for item in timeline.json()["transactions"] if item["id"] == entry_id)
    assert corrected_entry["was_corrected"] is True


@pytest.mark.asyncio
async def test_correction_cannot_edit_another_workers_diary(client: AsyncClient, auth_token, test_employer):
    response = await client.put(
        "/api/ledger/work/not-owned",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "employer_id": test_employer.id,
            "work_date": "2026-11-10",
            "days_worked": "1",
            "daily_wage": "700",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_correction_cannot_drop_below_already_allocated_payment(
    client: AsyncClient, auth_token, test_employer
):
    headers = {"Authorization": f"Bearer {auth_token}"}
    work = await client.post(
        "/api/ledger/work", headers=headers,
        json={"employer_id": test_employer.id, "work_date": "2026-11-11", "days_worked": "1", "daily_wage": "700"},
    )
    assert work.status_code == 201
    payment = await client.post(
        "/api/ledger/payments", headers=headers,
        json={"employer_id": test_employer.id, "payment_date": "2026-11-11", "amount": "200", "payment_type": "cash"},
    )
    assert payment.status_code == 201
    allocation = await client.post(
        f"/api/ledger/payments/{payment.json()['id']}/allocations", headers=headers,
        json={"work_entry_id": work.json()["id"], "amount": "200"},
    )
    assert allocation.status_code == 201

    correction = await client.put(
        f"/api/ledger/work/{work.json()['id']}", headers=headers,
        json={"employer_id": test_employer.id, "work_date": "2026-11-11", "days_worked": "1", "daily_wage": "100"},
    )
    assert correction.status_code == 422
    assert "allocated" in correction.json()["detail"].lower()
