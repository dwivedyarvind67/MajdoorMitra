"""Authenticated voice-recording, clarification, confirmation, and speech routes."""

import base64
import time
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Employer, Payment, StatementStatus, VoiceGenerationHistory, VoiceStatement, WorkEntry
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
    VoiceStudioRequest,
    VoiceStudioResponse,
    VoiceGenerationHistoryItem,
)
from app.services.conversation_service import get_conversation_service
from app.services.audit_service import AuditService
from app.services.evon_service import ExtractionError, get_evon_service
from app.services.extraction_service import get_extraction_service
from app.services.ledger_service import LedgerService
from app.services.prisma_service import ConfigurationError, TranscriptionError, get_prisma_service
from app.services.timbre_service import TTSError, get_timbre_service
from app.services.voice_capabilities import get_capabilities
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/voice", tags=["voice"])
MAX_AUDIO_BYTES = 12 * 1024 * 1024
EDITABLE_FIELDS = {
    "intent", "days_worked", "daily_wage", "hours_worked", "wage_basis",
    "hourly_rate", "overtime_hours", "overtime_multiplier", "work_date",
    "amount_received", "payment_type", "employer_name", "description",
}


@router.get("/capabilities")
async def voice_capabilities(worker_id: str = Depends(get_current_worker_id)):
    """Return provider-specific language, model, and voice support."""
    return get_capabilities()


@router.post("/studio/generate", response_model=VoiceStudioResponse)
async def generate_studio_speech(
    body: VoiceStudioRequest,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate actual Timbre audio and persist its worker-owned history metadata."""
    capabilities = get_capabilities()
    model = next((item for item in capabilities["timbre"]["models"] if item["id"] == body.model_id), None)
    voice = next((item for item in model["voices"] if item["id"] == body.voice_id), None) if model else None
    if not voice:
        raise HTTPException(status_code=422, detail="Choose a voice published for the selected speech model.")
    if body.language == "hi-en":
        raise HTTPException(status_code=422, detail="Hinglish is documented for another voice; that account/model combination has not been verified in this app yet.")
    if body.language == "auto" and body.model_id != "timbre-v3.0":
        raise HTTPException(status_code=422, detail="Automatic language detection is available here with Timbre v3.0.")
    if isinstance(voice["languages"], list) and body.language != "auto" and body.language not in voice["languages"]:
        raise HTTPException(status_code=422, detail="This Timbre v2.5 voice is optimized for a different language. Choose a matching language or a v3.0 voice.")

    if body.source_statement_id:
        source = await db.execute(select(VoiceStatement.id).where(
            VoiceStatement.id == body.source_statement_id,
            VoiceStatement.worker_id == worker_id,
            VoiceStatement.status == StatementStatus.CONFIRMED,
        ))
        if source.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="The confirmed voice record was not found.")

    generation_id = str(uuid.uuid4())
    started = time.perf_counter()
    try:
        audio = await get_timbre_service().speak(
            body.text,
            language=body.language,
            model=body.model_id,
            voice=body.voice_id,
            speed=float(body.speed),
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TTSError as exc:
        latency_ms = round((time.perf_counter() - started) * 1000)
        db.add(VoiceGenerationHistory(
            id=generation_id,
            worker_id=worker_id,
            source_statement_id=body.source_statement_id,
            text_input=body.text,
            language=body.language,
            model_id=body.model_id,
            voice_id=body.voice_id,
            status="failed",
            latency_ms=latency_ms,
            audio_retention_consent=False,
        ))
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Timbre could not generate audio. Your text and earlier records are safe; please retry.") from exc

    generated_at = datetime.now(timezone.utc)
    db.add(VoiceGenerationHistory(
        id=generation_id,
        worker_id=worker_id,
        source_statement_id=body.source_statement_id,
        text_input=body.text,
        language=body.language,
        model_id=body.model_id,
        voice_id=body.voice_id,
        status="success",
        latency_ms=latency_ms,
        audio_retention_consent=False,
    ))
    await db.commit()
    return VoiceStudioResponse(
        id=generation_id,
        text=body.text,
        language=body.language,
        model_id=body.model_id,
        voice_id=body.voice_id,
        status="success",
        latency_ms=latency_ms,
        audio_base64=base64.b64encode(audio).decode("ascii"),
        audio_content_type="audio/wav",
        created_at=generated_at,
    )


@router.get("/studio/history", response_model=list[VoiceGenerationHistoryItem])
async def get_studio_history(
    limit: int = 30,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="History limit must be between 1 and 100.")
    result = await db.execute(
        select(VoiceGenerationHistory)
        .where(VoiceGenerationHistory.worker_id == worker_id)
        .order_by(VoiceGenerationHistory.created_at.desc())
        .limit(limit)
    )
    return [
        VoiceGenerationHistoryItem(
            id=row.id,
            text_input=row.text_input,
            language=row.language,
            model_id=row.model_id,
            voice_id=row.voice_id,
            status=row.status,
            latency_ms=int(row.latency_ms) if row.latency_ms is not None else None,
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]


@router.delete("/studio/history/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_studio_history(
    generation_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VoiceGenerationHistory).where(
        VoiceGenerationHistory.id == generation_id,
        VoiceGenerationHistory.worker_id == worker_id,
    ))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Voice history was not found.")
    AuditService.record(db, worker_id, "voice.studio_history_deleted", "voice_generation", row.id, details={"status": row.status})
    await db.delete(row)
    await db.commit()
    return None


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
    await db.flush()
    AuditService.record(
        db,
        worker_id,
        "voice.session_created",
        "voice_statement",
        statement.id,
        source_statement_id=statement.id,
        details={"language": statement.language},
    )
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
    extracted["possible_duplicates"] = await _find_possible_duplicates(
        db, worker_id, extracted, statement.language
    )
    next_status = conversation.get_next_state("EXTRACTED", extracted)
    question = (
        conversation.generate_question(
            result.missing_fields, statement.language, result.intent, result.ambiguities
        )
        if result.missing_fields or result.ambiguities
        else conversation.generate_confirmation_message(extracted, statement.language)
    )

    statement.extracted_data = extracted
    statement.status = StatementStatus(next_status)
    AuditService.record(
        db,
        worker_id,
        "voice.details_extracted",
        "voice_statement",
        statement.id,
        source_statement_id=statement.id,
        details={"status": next_status, "fields": sorted(extracted.keys())},
    )
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
    if statement.status not in (StatementStatus.READY_FOR_CONFIRMATION, StatementStatus.AWAITING_INFORMATION):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review the extracted details before editing them.")

    corrections = body.corrections.model_dump(mode="json", exclude_unset=True)
    if not corrections:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Make a change before saving corrections.")

    current = dict(statement.extracted_data or {})
    candidate = {**current, **corrections, "missing_fields": [], "ambiguities": []}
    try:
        result = get_extraction_service().validate_and_fill(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more corrected values are invalid.") from exc
    extracted = result.model_dump(mode="json")
    extracted["possible_duplicates"] = await _find_possible_duplicates(
        db, worker_id, extracted, statement.language
    )
    conversation = get_conversation_service()
    statement.extracted_data = extracted
    statement.status = StatementStatus(conversation.get_next_state("EXTRACTED", extracted))
    statement.conversation_history = conversation.add_to_history(
        statement.conversation_history, "worker_correction", json_safe_corrections(corrections)
    )
    AuditService.record(
        db,
        worker_id,
        "voice.correction_applied",
        "voice_statement",
        statement.id,
        source_statement_id=statement.id,
        details={"fields": sorted(corrections.keys())},
    )
    question = (
        conversation.generate_question(
            result.missing_fields, statement.language, result.intent, result.ambiguities
        )
        if result.missing_fields or result.ambiguities
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
    if validated.missing_fields or validated.ambiguities or validated.intent not in {"log_work", "log_payment"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Required details are missing. Complete the follow-up before confirming.")

    employer_id = await _resolve_employer(db, worker_id, validated.employer_name, statement.id)
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
                    days_worked=validated.days_worked if validated.days_worked is not None else Decimal("0"),
                    hours_worked=validated.hours_worked,
                    daily_wage=validated.daily_wage,
                    wage_basis=validated.wage_basis,
                    hourly_rate=validated.hourly_rate,
                    overtime_hours=validated.overtime_hours or Decimal("0"),
                    overtime_multiplier=validated.overtime_multiplier or Decimal("1.5"),
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
        AuditService.record(
            db,
            worker_id,
            "voice.record_confirmed",
            "voice_statement",
            statement.id,
            source_statement_id=statement.id,
            details={
                "intent": validated.intent,
                "ledger_entity_id": work_entry_id or payment_id,
            },
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
    AuditService.record(
        db,
        worker_id,
        "voice.draft_rejected",
        "voice_statement",
        statement.id,
        source_statement_id=statement.id,
        details={"status": StatementStatus.REJECTED.value},
    )
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
        if statement.language == "hinglish":
            audio = await get_timbre_service().speak(
                text, language="auto", model="timbre-v3.0", voice="Shivani"
            )
        else:
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
    candidate["ambiguities"] = []
    try:
        result = get_extraction_service().validate_and_fill(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="That answer could not be checked. Please try again.") from exc

    conversation = get_conversation_service()
    extracted = result.model_dump(mode="json")
    extracted["possible_duplicates"] = await _find_possible_duplicates(
        db, statement.worker_id, extracted, statement.language
    )
    next_status = conversation.get_next_state(statement.status.value, extracted)
    question = (
        conversation.generate_question(
            result.missing_fields, statement.language, result.intent, result.ambiguities
        )
        if result.missing_fields or result.ambiguities
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
    AuditService.record(
        db,
        statement.worker_id,
        "voice.reply_applied",
        "voice_statement",
        statement.id,
        source_statement_id=statement.id,
        details={"fields": sorted(clean_updates.keys()), "status": next_status},
    )
    await db.commit()
    await db.refresh(statement)
    return ReplyResponse(
        id=statement.id,
        status=statement.status,
        extracted_data=ExtractionResultSchema(**extracted),
        question=question,
        transcript=transcript,
    )


async def _find_possible_duplicates(
    db: AsyncSession,
    worker_id: str,
    data: dict,
    language: str = "hi",
) -> list[dict]:
    """Compare the unconfirmed draft with same-worker records from that date."""
    if data.get("intent") not in {"log_work", "log_payment"} or not data.get("work_date"):
        return []
    try:
        record_date = datetime.strptime(data["work_date"], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return []
    start = datetime.combine(record_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    draft_employer = (data.get("employer_name") or "").strip().casefold()
    possible: list[dict] = []

    if data["intent"] == "log_work":
        rows = await db.execute(
            select(WorkEntry, Employer.name)
            .outerjoin(
                Employer,
                (Employer.id == WorkEntry.employer_id) & (Employer.worker_id == worker_id),
            )
            .where(
                WorkEntry.worker_id == worker_id,
                WorkEntry.work_date >= start,
                WorkEntry.work_date < end,
            )
            .order_by(WorkEntry.created_at.desc())
            .limit(20)
        )
        for entry, employer_name in rows.all():
            if draft_employer and (employer_name or "").strip().casefold() != draft_employer:
                continue
            same_basis = (entry.wage_basis or "daily") == data.get("wage_basis", "daily")
            same_units = Decimal(str(entry.days_worked or 0)) == Decimal(str(data.get("days_worked") or 0))
            same_hours = _same_decimal(entry.hours_worked, data.get("hours_worked"))
            same_rate = (
                _same_decimal(entry.daily_wage, data.get("daily_wage"))
                if data.get("wage_basis", "daily") == "daily"
                else _same_decimal(entry.hourly_rate, data.get("hourly_rate"))
            )
            same_overtime = (
                Decimal(str(entry.overtime_hours or 0)) == Decimal(str(data.get("overtime_hours") or 0))
                and Decimal(str(entry.overtime_multiplier or 1.5))
                == Decimal(str(data.get("overtime_multiplier") or 1.5))
            )
            exact = same_basis and same_units and same_hours and same_rate and same_overtime
            possible.append({
                "kind": "work",
                "record_id": entry.id,
                "date": record_date.isoformat(),
                "employer_name": employer_name,
                "amount": str(entry.total_earned),
                "exact": exact,
                "message": (
                    "इस तारीख और हिसाब का काम पहले से दर्ज है। दोबारा सेव करने से पहले जाँचें।"
                    if exact and language == "hi"
                    else "इस मालिक के लिए इसी तारीख का काम पहले से दर्ज है। यह अलग काम है तो विवरण जाँचकर जारी रखें।"
                    if language == "hi"
                    else "Work is already recorded for this employer and date. Check the details before continuing."
                ),
            })
    else:
        rows = await db.execute(
            select(Payment, Employer.name)
            .outerjoin(
                Employer,
                (Employer.id == Payment.employer_id) & (Employer.worker_id == worker_id),
            )
            .where(
                Payment.worker_id == worker_id,
                Payment.payment_date >= start,
                Payment.payment_date < end,
            )
            .order_by(Payment.created_at.desc())
            .limit(20)
        )
        draft_amount = Decimal(str(data.get("amount_received") or 0))
        for payment, employer_name in rows.all():
            if draft_employer and (employer_name or "").strip().casefold() != draft_employer:
                continue
            exact = (
                Decimal(str(payment.amount)) == draft_amount
                and (payment.payment_type.value if hasattr(payment.payment_type, "value") else str(payment.payment_type))
                == data.get("payment_type")
            )
            possible.append({
                "kind": "payment",
                "record_id": payment.id,
                "date": record_date.isoformat(),
                "employer_name": employer_name,
                "amount": str(payment.amount),
                "exact": exact,
                "message": (
                    "इसी तारीख और रकम का भुगतान पहले से दर्ज है। दोबारा सेव करने से पहले जाँचें।"
                    if exact and language == "hi"
                    else "इस मालिक का भुगतान इसी तारीख को पहले दर्ज हुआ है। रकम जाँचें।"
                    if language == "hi"
                    else "A payment is already recorded for this employer and date. Check the amount before continuing."
                ),
            })
    return possible[:5]


def _same_decimal(existing, proposed) -> bool:
    if existing is None or proposed is None:
        return existing is None and proposed is None
    try:
        return Decimal(str(existing)) == Decimal(str(proposed))
    except (TypeError, ValueError):
        return False


async def _resolve_employer(
    db: AsyncSession,
    worker_id: str,
    employer_name: str | None,
    source_statement_id: str | None = None,
) -> str | None:
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
        AuditService.record(
            db,
            worker_id,
            "employer.created_from_voice",
            "employer",
            employer.id,
            source_statement_id=source_statement_id,
            details={"name": normalized_name},
        )
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
