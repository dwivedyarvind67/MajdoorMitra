"""API-level workflow coverage with all three AI services isolated at the boundary."""

import base64
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.services.evon_service import ExtractionError
from app.services.prisma_service import TranscriptionError


WAVE = b"RIFF\x04\x00\x00\x00WAVE"
WORK_RECORD = {
    "intent": "log_work",
    "days_worked": "2.5",
    "daily_wage": "711.20",
    "hours_worked": None,
    "work_date": "2026-11-09",
    "employer_name": "Sharma Construction",
    "description": "Brick work",
}


class FakePrisma:
    def __init__(self, transcript="मैंने ढाई दिन काम किया, रोज़ 711 रुपये 20 पैसे"):
        self.transcript = transcript

    async def transcribe(self, *_args, **_kwargs):
        if isinstance(self.transcript, Exception):
            raise self.transcript
        return self.transcript


class FakeEvon:
    def __init__(self, extracted=None, reply=None, error=None):
        self.extracted = extracted or dict(WORK_RECORD)
        self.reply = reply or {}
        self.error = error

    async def extract(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.extracted

    async def extract_reply(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.reply


class FakeTimbre:
    async def speak(self, *_args, **_kwargs):
        return WAVE + b"spoken-audio"


def headers(token):
    return {"Authorization": f"Bearer {token}"}


async def create_session(client, token):
    response = await client.post("/api/voice/sessions", json={"language": "hi"}, headers=headers(token))
    assert response.status_code == 201
    return response.json()["id"]


async def upload_and_extract(client, token, session_id):
    uploaded = await client.post(
        f"/api/voice/sessions/{session_id}/audio",
        files={"audio": ("recording.wav", WAVE, "audio/wav")},
        headers=headers(token),
    )
    assert uploaded.status_code == 200
    extracted = await client.post(f"/api/voice/sessions/{session_id}/extract", headers=headers(token))
    return uploaded, extracted


@pytest.mark.asyncio
async def test_voice_work_is_only_saved_after_confirmation_and_returns_spoken_receipt(
    client: AsyncClient, test_worker, auth_token, monkeypatch
):
    from app.api import voice

    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    monkeypatch.setattr(voice, "get_evon_service", lambda: FakeEvon())
    monkeypatch.setattr(voice, "get_timbre_service", lambda: FakeTimbre())
    session_id = await create_session(client, auth_token)

    uploaded, extracted = await upload_and_extract(client, auth_token, session_id)
    assert uploaded.json()["transcript"].startswith("मैंने")
    assert extracted.status_code == 200
    assert extracted.json()["status"] == "READY_FOR_CONFIRMATION"

    before = await client.get("/api/ledger/summary", headers=headers(auth_token))
    assert Decimal(before.json()["total_earned"]) == Decimal("0.00")

    saved = await client.post(f"/api/voice/sessions/{session_id}/confirm", headers=headers(auth_token))
    assert saved.status_code == 200
    assert saved.json()["status"] == "CONFIRMED"
    assert saved.json()["work_entry_id"]

    repeated = await client.post(f"/api/voice/sessions/{session_id}/confirm", headers=headers(auth_token))
    assert repeated.status_code == 200
    assert repeated.json()["work_entry_id"] == saved.json()["work_entry_id"]

    summary = (await client.get("/api/ledger/summary", headers=headers(auth_token))).json()
    assert Decimal(summary["total_earned"]) == Decimal("1778.00")
    assert Decimal(summary["balance"]) == Decimal("1778.00")
    assert summary["employers"][0]["employer_name"] == "Sharma Construction"

    spoken = await client.post(f"/api/voice/sessions/{session_id}/speak", headers=headers(auth_token), json={})
    assert spoken.status_code == 200
    assert base64.b64decode(spoken.json()["audio_base64"]) == WAVE + b"spoken-audio"
    assert spoken.json()["audio_content_type"] == "audio/wav"


@pytest.mark.asyncio
async def test_missing_information_is_asked_and_follow_up_completes_record(
    client: AsyncClient, auth_token, monkeypatch
):
    from app.api import voice

    incomplete = {**WORK_RECORD, "daily_wage": None}
    fake_evon = FakeEvon(extracted=incomplete, reply={"daily_wage": "500.00"})
    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    monkeypatch.setattr(voice, "get_evon_service", lambda: fake_evon)
    session_id = await create_session(client, auth_token)
    _, extracted = await upload_and_extract(client, auth_token, session_id)

    assert extracted.json()["status"] == "AWAITING_INFORMATION"
    assert extracted.json()["extracted_data"]["missing_fields"] == ["daily_wage"]
    assert "दैनिक" in extracted.json()["question"]

    reply = await client.post(
        f"/api/voice/sessions/{session_id}/reply",
        json={"text": "पाँच सौ रुपये"},
        headers=headers(auth_token),
    )
    assert reply.status_code == 200
    assert reply.json()["status"] == "READY_FOR_CONFIRMATION"
    assert Decimal(reply.json()["extracted_data"]["daily_wage"]) == Decimal("500.00")
    assert reply.json()["extracted_data"]["missing_fields"] == []

    summary = (await client.get("/api/ledger/summary", headers=headers(auth_token))).json()
    assert Decimal(summary["total_earned"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_spoken_correction_keeps_original_transcript_visible(
    client: AsyncClient, auth_token, monkeypatch
):
    from app.api import voice

    fake_evon = FakeEvon(reply={"daily_wage": "750.00"})
    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    monkeypatch.setattr(voice, "get_evon_service", lambda: fake_evon)
    session_id = await create_session(client, auth_token)
    await upload_and_extract(client, auth_token, session_id)

    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma("सुधार: रोज़ सात सौ पचास रुपये"))
    corrected = await client.post(
        f"/api/voice/sessions/{session_id}/reply/audio",
        files={"audio": ("correction.wav", WAVE, "audio/wav")},
        headers=headers(auth_token),
    )
    assert corrected.status_code == 200
    assert corrected.json()["transcript"] == "सुधार: रोज़ सात सौ पचास रुपये"
    assert Decimal(corrected.json()["extracted_data"]["daily_wage"]) == Decimal("750.00")

    detail = (await client.get(f"/api/statements/{session_id}", headers=headers(auth_token))).json()
    assert detail["transcript"] == FakePrisma().transcript
    assert any(item["role"] == "worker_transcript" for item in detail["conversation_history"])

    saved = await client.post(f"/api/voice/sessions/{session_id}/confirm", headers=headers(auth_token))
    assert saved.status_code == 200
    summary = (await client.get("/api/ledger/summary", headers=headers(auth_token))).json()
    assert Decimal(summary["total_earned"]) == Decimal("1875.00")


@pytest.mark.asyncio
async def test_failed_prisma_and_evon_calls_preserve_session_and_ledger(
    client: AsyncClient, auth_token, monkeypatch
):
    from app.api import voice

    session_id = await create_session(client, auth_token)
    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma(TranscriptionError("offline")))
    upload = await client.post(
        f"/api/voice/sessions/{session_id}/audio",
        files={"audio": ("recording.wav", WAVE, "audio/wav")},
        headers=headers(auth_token),
    )
    assert upload.status_code == 502
    detail = (await client.get(f"/api/statements/{session_id}", headers=headers(auth_token))).json()
    assert detail["status"] == "INITIAL"
    assert detail["transcript"] is None

    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    uploaded = await client.post(
        f"/api/voice/sessions/{session_id}/audio",
        files={"audio": ("recording.wav", WAVE, "audio/wav")},
        headers=headers(auth_token),
    )
    assert uploaded.status_code == 200
    monkeypatch.setattr(voice, "get_evon_service", lambda: FakeEvon(error=ExtractionError("offline")))
    extraction = await client.post(f"/api/voice/sessions/{session_id}/extract", headers=headers(auth_token))
    assert extraction.status_code == 502

    detail = (await client.get(f"/api/statements/{session_id}", headers=headers(auth_token))).json()
    assert detail["status"] == "TRANSCRIBED"
    assert detail["transcript"] == FakePrisma().transcript
    assert detail["extracted_data"] is None
    summary = (await client.get("/api/ledger/summary", headers=headers(auth_token))).json()
    assert Decimal(summary["total_earned"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_rejected_draft_cannot_be_confirmed_or_downloaded_as_a_statement(
    client: AsyncClient, auth_token, monkeypatch
):
    from app.api import voice

    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    monkeypatch.setattr(voice, "get_evon_service", lambda: FakeEvon())
    session_id = await create_session(client, auth_token)
    await upload_and_extract(client, auth_token, session_id)

    rejected = await client.post(f"/api/voice/sessions/{session_id}/reject", headers=headers(auth_token))
    assert rejected.status_code == 200
    confirm = await client.post(f"/api/voice/sessions/{session_id}/confirm", headers=headers(auth_token))
    assert confirm.status_code == 409
    pdf = await client.get(f"/api/statements/{session_id}/pdf", headers=headers(auth_token))
    assert pdf.status_code == 409
    transactions = (await client.get("/api/ledger/transactions", headers=headers(auth_token))).json()
    assert transactions["total_count"] == 0


@pytest.mark.asyncio
async def test_partial_payment_and_advance_are_summarized_per_employer(
    client: AsyncClient, auth_token, monkeypatch
):
    from app.api import voice

    monkeypatch.setattr(voice, "get_prisma_service", lambda: FakePrisma())
    monkeypatch.setattr(voice, "get_evon_service", lambda: FakeEvon())
    session_id = await create_session(client, auth_token)
    await upload_and_extract(client, auth_token, session_id)
    await client.post(f"/api/voice/sessions/{session_id}/confirm", headers=headers(auth_token))

    pay_evon = FakeEvon(extracted={
        "intent": "log_payment", "amount_received": "600.00", "payment_type": "cash",
        "work_date": "2026-11-10", "employer_name": "Sharma Construction",
    })
    monkeypatch.setattr(voice, "get_evon_service", lambda: pay_evon)
    payment_session = await create_session(client, auth_token)
    await upload_and_extract(client, auth_token, payment_session)
    payment = await client.post(f"/api/voice/sessions/{payment_session}/confirm", headers=headers(auth_token))
    assert payment.json()["payment_id"]

    advance_evon = FakeEvon(extracted={
        "intent": "log_payment", "amount_received": "200.00", "payment_type": "advance",
        "work_date": "2026-11-10", "employer_name": "Patel Site",
    })
    monkeypatch.setattr(voice, "get_evon_service", lambda: advance_evon)
    advance_session = await create_session(client, auth_token)
    await upload_and_extract(client, auth_token, advance_session)
    advance = await client.post(f"/api/voice/sessions/{advance_session}/confirm", headers=headers(auth_token))
    assert advance.json()["payment_id"]

    summary = (await client.get("/api/ledger/summary", headers=headers(auth_token))).json()
    assert Decimal(summary["total_earned"]) == Decimal("1778.00")
    assert Decimal(summary["total_received"]) == Decimal("800.00")
    assert Decimal(summary["total_advances"]) == Decimal("200.00")
    assert Decimal(summary["balance"]) == Decimal("978.00")
    assert Decimal(summary["pending"]) == Decimal("978.00")
    by_employer = {row["employer_name"]: row for row in summary["employers"]}
    assert Decimal(by_employer["Sharma Construction"]["balance"]) == Decimal("1178.00")
    assert Decimal(by_employer["Patel Site"]["overpaid"]) == Decimal("200.00")


@pytest.mark.asyncio
async def test_manual_duplicate_payments_and_cross_worker_employer_are_rejected(
    client: AsyncClient, test_employer, auth_token
):
    from app.api import voice

    payload = {
        "employer_id": test_employer.id,
        "amount": "400.00",
        "payment_date": date(2026, 11, 10).isoformat(),
        "payment_type": "upi",
        "notes": "Partial wage",
    }
    first = await client.post("/api/ledger/payments", json=payload, headers=headers(auth_token))
    assert first.status_code == 201
    duplicate = await client.post("/api/ledger/payments", json=payload, headers=headers(auth_token))
    assert duplicate.status_code == 409

    from app.utils.auth import create_access_token

    # A foreign employer id is rejected by the ledger API before it can leak into another account.
    other_token = create_access_token({"sub": "not-this-worker"})
    foreign = await client.post("/api/ledger/payments", json=payload, headers=headers(other_token))
    assert foreign.status_code == 404
