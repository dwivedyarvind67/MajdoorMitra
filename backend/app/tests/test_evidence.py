"""Consent, validation, private storage, and ownership tests for evidence files."""

from datetime import datetime, timezone
import uuid

import pytest
from httpx import AsyncClient

from app.api import evidence as evidence_api
from app.models.models import Employer, Worker, WorkEntry
from app.utils.auth import hash_pin


@pytest.mark.asyncio
async def test_evidence_requires_consent_and_validates_file_signature(client: AsyncClient, auth_token, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_api, "STORAGE_ROOT", tmp_path)
    headers = {"Authorization": f"Bearer {auth_token}"}

    no_consent = await client.post(
        "/api/evidence", headers=headers,
        data={"document_type": "payment_receipt"},
        files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )
    assert no_consent.status_code == 422
    assert list(tmp_path.iterdir()) == []

    fake = await client.post(
        "/api/evidence", headers=headers,
        data={"consent_given": "true", "document_type": "payment_receipt"},
        files={"file": ("fake.pdf", b"not actually a pdf", "application/pdf")},
    )
    assert fake.status_code == 415
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_evidence_upload_download_list_and_delete(client: AsyncClient, auth_token, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_api, "STORAGE_ROOT", tmp_path)
    headers = {"Authorization": f"Bearer {auth_token}"}
    png = b"\x89PNG\r\n\x1a\n" + b"sample image bytes"
    uploaded = await client.post(
        "/api/evidence", headers=headers,
        data={"consent_given": "true", "document_type": "payment_receipt"},
        files={"file": ("..\\private\\receipt.png", png, "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    item = uploaded.json()
    assert item["file_name"] == "receipt.png"
    assert item["content_type"] == "image/png"
    assert item["size_bytes"] == len(png)
    assert len(list(tmp_path.iterdir())) == 1

    listed = await client.get("/api/evidence", headers=headers)
    assert listed.status_code == 200
    assert [record["id"] for record in listed.json()] == [item["id"]]

    preview = await client.get(f"/api/evidence/{item['id']}/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content == png

    downloaded = await client.get(f"/api/evidence/{item['id']}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == png
    assert "attachment" in downloaded.headers["content-disposition"]

    deleted = await client.delete(f"/api/evidence/{item['id']}", headers=headers)
    assert deleted.status_code == 204
    assert list(tmp_path.iterdir()) == []
    assert (await client.get("/api/evidence", headers=headers)).json() == []


@pytest.mark.asyncio
async def test_evidence_cannot_link_to_another_workers_record(
    client: AsyncClient, auth_token, test_worker, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr(evidence_api, "STORAGE_ROOT", tmp_path)
    other_worker = Worker(
        id=str(uuid.uuid4()), name="Other worker", phone="9876500022",
        preferred_language="hi", pin_hash=hash_pin("1234"),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(other_worker)
    await db_session.flush()
    employer = Employer(
        id=str(uuid.uuid4()), worker_id=other_worker.id, name="Other employer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(employer)
    await db_session.flush()
    entry = WorkEntry(
        id=str(uuid.uuid4()), worker_id=other_worker.id, employer_id=employer.id,
        work_date=datetime.now(timezone.utc), days_worked=1, hours_worked=None,
        wage_basis="daily", hourly_rate=None, overtime_hours=0,
        overtime_multiplier=1.5, daily_wage=700, total_earned=700,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(entry)
    await db_session.commit()

    response = await client.post(
        "/api/evidence", headers={"Authorization": f"Bearer {auth_token}"},
        data={"consent_given": "true", "document_type": "payment_receipt", "work_entry_id": entry.id},
        files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\nbytes", "image/png")},
    )
    assert response.status_code == 404
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_evidence_access_is_worker_scoped(client: AsyncClient, auth_token, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_api, "STORAGE_ROOT", tmp_path)
    uploaded = await client.post(
        "/api/evidence",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"consent_given": "true", "document_type": "other"},
        files={"file": ("receipt.pdf", b"%PDF-1.7\ncontents", "application/pdf")},
    )
    assert uploaded.status_code == 201
    evidence_id = uploaded.json()["id"]

    from app.utils.auth import create_access_token
    other_token = create_access_token({"sub": str(uuid.uuid4())})
    assert (await client.get(f"/api/evidence/{evidence_id}/download", headers={"Authorization": f"Bearer {other_token}"})).status_code == 404
    assert (await client.delete(f"/api/evidence/{evidence_id}", headers={"Authorization": f"Bearer {other_token}"})).status_code == 404
