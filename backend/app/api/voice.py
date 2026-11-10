"""Authenticated voice-recording, clarification, confirmation, and speech routes."""

import base64
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer, Payment, StatementStatus, VoiceStatement, WorkEntry
from app.schemas.ledger import PaymentCreate, WorkEntryCreate
from app.schemas.voice import (
    ConfirmResponse,
    CorrectionRequest,
    ExtractionResult as ExtractionResultSchema,
    ExtractionResponse,
    ReplyRequest,
    ReplyResponse,
    SpeakRequest,
    SpeakResponse,
    TranscriptionResponse,
    VoiceSessionCreate,
    VoiceSessionResponse,
)
from app.services.conversation_service import get_conversation_service
from app.services.evon_service import ExtractionError, get_evon_service
from app.services.extraction_service import get_extraction_service
from app.services.ledger_service import LedgerService
from app.services.prisma_service import ConfigurationError, TranscriptionError, get_prisma_service
from app.services.timbre_service import TTSError, get_timbre_service
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/voice", tags=["voice"])
MAX_AUDIO_BYTES = 12 * 1024 * 1024
EDITABLE_FIELDS = {
    "intent", "days_worked", "daily_wage", "hours_worked", "work_date",
    "amount_received", "payment_type", "employer_name", "description",
}


@router.post("/sessions", response_model=VoiceSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: VoiceSessionCreate,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    statement = VoiceStatement(
        id=str(uuid.uuid4()),
        worker_id=worker_id,
        language=body.language,
        status=StatementStatus.INITIAL,
        conversation_history=[],
        created_at=datetime.now(timezone.utc),
    )
    db.add(statement)
    await db.commit()
    await db.refresh(statement)
    return VoiceSessionResponse(
        id=statement.id,
        status=statement.status,
        language=statement.language,
        created_at=statement.created_at,
    )


@router.post("/sessions/{session_id}/audio", response_model=TranscriptionResponse)
async def upload_audio(
    session_id: str,
    audio: UploadFile = File(...),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe a WAV recording. Session state changes only after Prisma succeeds."""
    statement = await _get_session(db, session_id, worker_id)
    if statement.status not in (StatementStatus.INITIAL, StatementStatus.TRANSCRIBED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session is already in follow-up or confirmation. Use the correction voice action.",
        )

    audio_data = await audio.read(MAX_AUDIO_BYTES + 1)
    if not audio_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The recording is empty. Please record again.")
    if len(audio_data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Recording is too large. Keep it under 12 MB.")
    if not _is_wave(audio_data):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Please send the recording as a WAV audio file.")

    try:
        transcript = await get_prisma_service().transcribe(
            audio_data,
            statement.language,
            filename="recording.wav",
            content_type="audio/wav",
        )
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech recognition failed. Your earlier record is unchanged; please try again.") from exc

    conversation = get_conversation_service()
    statement.transcript = transcript
    statement.status = StatementStatus.TRANSCRIBED
    statement.conversation_history = conversation.add_to_history(
        statement.conversation_history, "worker_transcript", transcript
    )
    await db.commit()
    await db.refresh(statement)
    return TranscriptionResponse(id=statement.id, transcript=transcript, status=statement.status)


@router.post("/sessions/{session_id}/extract", response_model=ExtractionResponse)
async def extract_data(
    session_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Extract the transcript with Evon; a provider failure leaves it untouched."""
    statement = await _get_session(db, session_id, worker_id)
    if statement.status != StatementStatus.TRANSCRIBED or not statement.transcript:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Record audio before extracting details.")

    try:
        raw_data = await get_evon_service().extract(statement.transcript, statement.language)
        result = get_extraction_service().validate_and_fill(raw_data)
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The assistant could not read this statement. Your transcript is saved; please try extraction again.") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The assistant returned details that could not be checked. Your transcript is saved; please try again.") from exc

    conversation = get_conversation_service()
    extracted = result.model_dump(mode="json")
    next_status = conversation.get_next_state("EXTRACTED", extracted)
    question = (
        conversation.generate_question(result.missing_fields, statement.language, result.intent)
        if result.missing_fields
        else conversation.generate_confirmation_message(extracted, statement.language)
    )

    statement.extracted_data = extracted
    statement.status = StatementStatus(next_status)
    history = conversation.add_to_history(statement.conversation_history, "assistant_extraction", "Details extracted for worker review.")
    if question:
        history = conversation.add_to_history(history, "assistant", question)
    statement.conversation_history = history
    await db.commit()
    await db.refresh(statement)
    return ExtractionResponse(
        id=statement.id,
        status=statement.status,
        extracted_data=ExtractionResultSchema(**extracted),
        question=question,
        conversation_history=statement.conversation_history,
    )


@router.post("/sessions/{session_id}/reply", response_model=ReplyResponse)
async def reply_to_session(
    session_id: str,
    body: ReplyRequest,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    statement = await _get_session(db, session_id, worker_id)
    result = await _apply_reply(statement, body.text, None, db)
    return result


@router.post("/sessions/{session_id}/reply/audio", response_model=ReplyResponse)
async def reply_with_audio(
    session_id: str,
    audio: UploadFile = File(...),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe a spoken answer/correction without replacing the original transcript."""
    statement = await _get_session(db, session_id, worker_id)
    audio_data = await audio.read(MAX_AUDIO_BYTES + 1)
    if not audio_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The recording is empty. Please record again.")
    if len(audio_data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Recording is too large. Keep it under 12 MB.")
    if not _is_wave(audio_data):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Please send the recording as a WAV audio file.")
    try:
        transcript = await get_prisma_service().transcribe(
            audio_data, statement.language, filename="clarification.wav", content_type="audio/wav"
        )
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech recognition failed. Your record is unchanged; please try again.") from exc

    return await _apply_reply(statement, transcript, transcript, db)


@router.post("/sessions/{session_id}/correct", response_model=ReplyResponse)
async def correct_extraction(
    session_id: str,
    body: CorrectionRequest,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Apply explicit form corrections while leaving the record unconfirmed."""
    statement = await _get_session(db, session_id, worker_id)
    if statement.status != StatementStatus.READY_FOR_CONFIRMATION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review the extracted details before editing them.")

    corrections = body.corrections.model_dump(mode="json", exclude_unset=True)
    if not corrections:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Make a change before saving corrections.")

    current = dict(statement.extracted_data or {})
    candidate = {**current, **corrections, "missing_fields": []}
    try:
        result = get_extraction_service().validate_and_fill(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more corrected values are invalid.") from exc
    extracted = result.model_dump(mode="json")
    conversation = get_conversation_service()
    statement.extracted_data = extracted
    statement.status = StatementStatus(conversation.get_next_state("EXTRACTED", extracted))
    statement.conversation_history = conversation.add_to_history(
        statement.conversation_history, "worker_correction", json_safe_corrections(corrections)
    )
    question = (
        conversation.generate_question(result.missing_fields, statement.language, result.intent)
        if result.missing_fields
        else conversation.generate_confirmation_message(extracted, statement.language)
    )
    await db.commit()
    await db.refresh(statement)
    return ReplyResponse(
        id=statement.id,
        status=statement.status,
        extracted_data=ExtractionResultSchema(**extracted),
        question=question,
    )


@router.post("/sessions/{session_id}/confirm", response_model=ConfirmResponse)
async def confirm_session(
    session_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Atomically save exactly one worker-confirmed ledger record and its timestamp."""
    statement = await _get_session(db, session_id, worker_id)
    if statement.status == StatementStatus.CONFIRMED:
        work = await db.execute(select(WorkEntry.id).where(WorkEntry.worker_id == worker_id, WorkEntry.source_statement_id == statement.id))
        payment = await db.execute(select(Payment.id).where(Payment.worker_id == worker_id, Payment.source_statement_id == statement.id))
        return ConfirmResponse(
            id=statement.id,
            status=statement.status,
            work_entry_id=work.scalar_one_or_none(),
            payment_id=payment.scalar_one_or_none(),
            message="This record was already confirmed.",
        )
    if statement.status != StatementStatus.READY_FOR_CONFIRMATION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Answer the assistant's question and review the details before confirming.")

    extracted = dict(statement.extracted_data or {})
    try:
        validated = get_extraction_service().validate_and_fill(extracted)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The extracted details need to be reviewed again before saving.") from exc
    if validated.missing_fields or validated.intent not in {"log_work", "log_payment"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Required details are missing. Complete the follow-up before confirming.")

    employer_id = await _resolve_employer(db, worker_id, validated.employer_name)
    ledger = LedgerService()
    work_entry_id = None
    payment_id = None
    try:
        if validated.intent == "log_work":
            work_entry = await ledger.create_work_entry(
                db,
                worker_id,
                WorkEntryCreate(
                    employer_id=employer_id,
                    work_date=datetime.strptime(validated.work_date, "%Y-%m-%d").date(),
                    days_worked=validated.days_worked,
                    hours_worked=validated.hours_worked,
                    daily_wage=validated.daily_wage,
                    description=validated.description,
                ),
                source_statement_id=statement.id,
            )
            work_entry_id = work_entry.id
        else:
            payment = await ledger.create_payment(
                db,
                worker_id,
                PaymentCreate(
                    employer_id=employer_id,
                    amount=validated.amount_received,
                    payment_date=datetime.strptime(validated.work_date, "%Y-%m-%d").date(),
                    payment_type=validated.payment_type,
                    notes=validated.description,
                ),
                source_statement_id=statement.id,
            )
            payment_id = payment.id

        conversation = get_conversation_service()
        statement.status = StatementStatus.CONFIRMED
        statement.confirmed_at = datetime.now(timezone.utc)
        statement.conversation_history = conversation.add_to_history(
            statement.conversation_history, "system", "Worker confirmed the details and saved the record."
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The record could not be saved. Nothing was confirmed; please try again.") from exc

    return ConfirmResponse(
        id=statement.id,
        status=statement.status,
        work_entry_id=work_entry_id,
        payment_id=payment_id,
        message="Record saved after your confirmation.",
    )


@router.post("/sessions/{session_id}/reject", response_model=ConfirmResponse)
async def reject_session(
    session_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    statement = await _get_session(db, session_id, worker_id)
    if statement.status == StatementStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A saved record cannot be discarded from this screen.")
    if statement.status == StatementStatus.REJECTED:
        return ConfirmResponse(id=statement.id, status=statement.status, message="This draft was already discarded.")
    conversation = get_conversation_service()
    statement.status = StatementStatus.REJECTED
    statement.conversation_history = conversation.add_to_history(statement.conversation_history, "system", "Worker discarded this draft.")
    await db.commit()
    return ConfirmResponse(id=statement.id, status=statement.status, message="Draft discarded. No ledger record was saved.")


@router.post("/sessions/{session_id}/speak", response_model=SpeakResponse)
async def speak_summary(
    session_id: str,
    body: SpeakRequest = SpeakRequest(),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    statement = await _get_session(db, session_id, worker_id)
    if statement.status != StatementStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirm the record before generating its spoken receipt.")
    text = body.text
    if not text:
        text = get_conversation_service().generate_receipt_message(
            dict(statement.extracted_data or {}), statement.language
        )
    try:
        audio = await get_timbre_service().speak(text, statement.language)
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TTSError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech generation failed. Your saved record is safe; try speaking the receipt again.") from exc
    return SpeakResponse(
        text=text,
        audio_base64=base64.b64encode(audio).decode("ascii"),
        audio_content_type="audio/wav",
    )


async def _apply_reply(
    statement: VoiceStatement,
    reply_text: str,
    transcript: str | None,
    db: AsyncSession,
) -> ReplyResponse:
    if statement.status not in (
        StatementStatus.EXTRACTED,
        StatementStatus.AWAITING_INFORMATION,
        StatementStatus.READY_FOR_CONFIRMATION,
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session is not waiting for an answer or correction.")

    current = dict(statement.extracted_data or {})
    try:
        updates = await get_evon_service().extract_reply(reply_text, current, statement.language)
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The assistant could not understand that answer. Your saved details are unchanged; please try again.") from exc

    clean_updates = {
        key: value for key, value in updates.items()
        if key in EDITABLE_FIELDS and value is not None
    }
    if not clean_updates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="I couldn't read a new detail from that answer. Please say the value clearly and try again.")

    candidate = {**current, **clean_updates}
    candidate["missing_fields"] = [field for field in current.get("missing_fields", []) if field not in clean_updates]
    candidate["ambiguities"] = current.get("ambiguities", [])
    try:
        result = get_extraction_service().validate_and_fill(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="That answer could not be checked. Please try again.") from exc

    conversation = get_conversation_service()
    extracted = result.model_dump(mode="json")
    next_status = conversation.get_next_state(statement.status.value, extracted)
    question = (
        conversation.generate_question(result.missing_fields, statement.language, result.intent)
        if result.missing_fields
        else conversation.generate_confirmation_message(extracted, statement.language)
    )

    history = conversation.add_to_history(statement.conversation_history, "worker", reply_text)
    if transcript:
        history = conversation.add_to_history(history, "worker_transcript", transcript)
    if question:
        history = conversation.add_to_history(history, "assistant", question)
    statement.conversation_history = history
    statement.extracted_data = extracted
    statement.status = StatementStatus(next_status)
    await db.commit()
    await db.refresh(statement)
    return ReplyResponse(
        id=statement.id,
        status=statement.status,
        extracted_data=ExtractionResultSchema(**extracted),
        question=question,
        transcript=transcript,
    )


async def _resolve_employer(db: AsyncSession, worker_id: str, employer_name: str | None) -> str | None:
    if not employer_name:
        return None
    normalized_name = employer_name.strip()
    result = await db.execute(
        select(Employer).where(Employer.worker_id == worker_id, Employer.name == normalized_name)
    )
    employer = result.scalar_one_or_none()
    if employer is None:
        employer = Employer(id=str(uuid.uuid4()), worker_id=worker_id, name=normalized_name)
        db.add(employer)
        await db.flush()
    return employer.id


async def _get_session(db: AsyncSession, session_id: str, worker_id: str) -> VoiceStatement:
    result = await db.execute(
        select(VoiceStatement).where(VoiceStatement.id == session_id, VoiceStatement.worker_id == worker_id)
    )
    statement = result.scalar_one_or_none()
    if statement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice session not found.")
    return statement


def _is_wave(audio_data: bytes) -> bool:
    return len(audio_data) >= 12 and audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE"


def json_safe_corrections(corrections: dict) -> str:
    """Serialize an already validated correction without leaking provider credentials."""
    return ", ".join(f"{key}: {value}" for key, value in corrections.items())
