"""Private, consent-gated evidence storage for worker-owned ledger records."""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import EvidenceFile, Payment, VoiceStatement, WorkEntry
from app.schemas.evidence import EvidenceKind, EvidenceResponse
from app.services.audit_service import AuditService
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/evidence", tags=["evidence"])
STORAGE_ROOT = Path(__file__).resolve().parents[2] / ".private-evidence"
MAX_FILE_BYTES = 12 * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
}


def _detect_content_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    return None


def _safe_path(file_reference: str) -> Path:
    root = STORAGE_ROOT.resolve()
    path = (root / file_reference).resolve()
    if path.parent != root:
        raise HTTPException(status_code=500, detail="Evidence storage reference is invalid.")
    return path


def _safe_filename(raw_name: str | None) -> str:
    name = (raw_name or "evidence").replace("\\", "/").split("/")[-1]
    name = "".join(character for character in name if character.isprintable()).strip()
    return (name or "evidence")[:255]


async def _assert_owned_link(
    db: AsyncSession,
    worker_id: str,
    model,
    record_id: str | None,
    label: str,
) -> None:
    if not record_id:
        return
    result = await db.execute(select(model.id).where(model.id == record_id, model.worker_id == worker_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"{label} not found.")


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    consent_given: bool = Form(False),
    document_type: EvidenceKind = Form("other"),
    statement_id: str | None = Form(None),
    work_entry_id: str | None = Form(None),
    payment_id: str | None = Form(None),
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Store an allowed file only after explicit consent and ownership checks."""
    if not consent_given:
        raise HTTPException(status_code=422, detail="Please confirm that you want to store this file.")
    if document_type not in {"payment_receipt", "wage_agreement", "work_document", "audio", "other"}:
        raise HTTPException(status_code=422, detail="Choose a supported evidence type.")
    links = [statement_id, work_entry_id, payment_id]
    if sum(link is not None for link in links) > 1:
        raise HTTPException(status_code=422, detail="Link one evidence file to only one ledger record.")
    await _assert_owned_link(db, worker_id, VoiceStatement, statement_id, "Statement")
    await _assert_owned_link(db, worker_id, WorkEntry, work_entry_id, "Work entry")
    await _assert_owned_link(db, worker_id, Payment, payment_id, "Payment")

    content = await file.read(MAX_FILE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="The selected file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Evidence files must be 12 MB or smaller.")
    content_type = _detect_content_type(content)
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Use a PDF, JPEG, PNG, WebP, WAV, or WebM file.")
    if document_type == "audio" and not content_type.startswith("audio/"):
        raise HTTPException(status_code=422, detail="Audio evidence must be a WAV or WebM recording.")
    if document_type != "audio" and content_type.startswith("audio/"):
        raise HTTPException(status_code=422, detail="Choose the audio evidence type for a recording.")

    evidence_id = str(uuid.uuid4())
    storage_name = f"{uuid.uuid4().hex}{ALLOWED_TYPES[content_type]}"
    path = _safe_path(storage_name)
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    filename = _safe_filename(file.filename)
    evidence = EvidenceFile(
        id=evidence_id,
        worker_id=worker_id,
        statement_id=statement_id,
        work_entry_id=work_entry_id,
        payment_id=payment_id,
        file_reference=storage_name,
        file_name=filename,
        document_type=document_type,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        consent_given=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(evidence)
    AuditService.record(
        db, worker_id, "evidence.uploaded", "evidence_file", evidence.id,
        source_statement_id=statement_id,
        details={"document_type": document_type, "content_type": content_type, "size_bytes": len(content)},
    )
    try:
        await db.commit()
        await db.refresh(evidence)
    except Exception:
        await db.rollback()
        path.unlink(missing_ok=True)
        raise
    return evidence


@router.get("", response_model=list[EvidenceResponse])
async def list_evidence(
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """List only the authenticated worker's file metadata."""
    result = await db.execute(
        select(EvidenceFile).where(EvidenceFile.worker_id == worker_id).order_by(EvidenceFile.created_at.desc())
    )
    return result.scalars().all()


async def _get_worker_evidence(db: AsyncSession, worker_id: str, evidence_id: str) -> EvidenceFile:
    result = await db.execute(
        select(EvidenceFile).where(EvidenceFile.id == evidence_id, EvidenceFile.worker_id == worker_id)
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    return evidence


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Download a private file as an attachment after worker ownership check."""
    evidence = await _get_worker_evidence(db, worker_id, evidence_id)
    path = _safe_path(evidence.file_reference)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence content is unavailable.")
    return Response(
        content=path.read_bytes(),
        media_type=evidence.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(_safe_filename(evidence.file_name))}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{evidence_id}/preview")
async def preview_evidence(
    evidence_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Inline preview of sniffed image, PDF, or audio formats."""
    evidence = await _get_worker_evidence(db, worker_id, evidence_id)
    if evidence.content_type not in {"application/pdf", "image/jpeg", "image/png", "image/webp", "audio/wav", "audio/webm"}:
        raise HTTPException(status_code=415, detail="Preview is not available for this file type.")
    path = _safe_path(evidence.file_reference)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence content is unavailable.")
    return Response(
        content=path.read_bytes(),
        media_type=evidence.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(_safe_filename(evidence.file_name))}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: str,
    worker_id: str = Depends(get_current_worker_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete metadata and private content for one worker-owned file."""
    evidence = await _get_worker_evidence(db, worker_id, evidence_id)
    path = _safe_path(evidence.file_reference)
    staged_path = _safe_path(f".{evidence.id}.deleting")
    if path.exists():
        os.replace(path, staged_path)
    AuditService.record(
        db, worker_id, "evidence.deleted", "evidence_file", evidence.id,
        source_statement_id=evidence.statement_id,
        details={"document_type": evidence.document_type},
    )
    await db.delete(evidence)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        if staged_path.exists():
            os.replace(staged_path, path)
        raise
    staged_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
