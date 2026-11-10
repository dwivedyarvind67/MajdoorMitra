"""
SQLAlchemy ORM models for MazdoorMitra.
All financial columns use NUMERIC(15,2). Primary keys are String UUIDs for
cross-database (PostgreSQL / SQLite) compatibility.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class StatementStatus(str, enum.Enum):
    """Lifecycle status of a voice statement."""
    INITIAL = "INITIAL"
    TRANSCRIBED = "TRANSCRIBED"
    EXTRACTED = "EXTRACTED"
    AWAITING_INFORMATION = "AWAITING_INFORMATION"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class PaymentType(str, enum.Enum):
    """Type of payment received by a worker."""
    CASH = "cash"
    UPI = "upi"
    BANK = "bank"
    ADVANCE = "advance"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Worker(Base):
    """Registered worker / labourer."""
    __tablename__ = "workers"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    preferred_language = Column(String(10), nullable=False, default="hi")
    pin_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    employers = relationship("Employer", back_populates="worker", lazy="selectin")
    work_entries = relationship("WorkEntry", back_populates="worker", lazy="selectin")
    payments = relationship("Payment", back_populates="worker", lazy="selectin")
    voice_statements = relationship("VoiceStatement", back_populates="worker", lazy="selectin")
    evidence_files = relationship("EvidenceFile", back_populates="worker", lazy="selectin")


class Employer(Base):
    """Employer associated with a worker."""
    __tablename__ = "employers"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    contact_details = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    worker = relationship("Worker", back_populates="employers")
    work_entries = relationship("WorkEntry", back_populates="employer", lazy="selectin")
    payments = relationship("Payment", back_populates="employer", lazy="selectin")


class WorkEntry(Base):
    """Record of work performed by a worker."""
    __tablename__ = "work_entries"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employer_id = Column(
        String(36),
        ForeignKey("employers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    work_date = Column(DateTime(timezone=True), nullable=False)
    days_worked = Column(Numeric(15, 2), nullable=False)
    hours_worked = Column(Numeric(15, 2), nullable=True)
    daily_wage = Column(Numeric(15, 2), nullable=False)
    total_earned = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=True)
    source_statement_id = Column(
        String(36),
        ForeignKey("voice_statements.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    worker = relationship("Worker", back_populates="work_entries")
    employer = relationship("Employer", back_populates="work_entries")
    source_statement = relationship("VoiceStatement", back_populates="work_entries")


class Payment(Base):
    """Payment received by a worker."""
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employer_id = Column(
        String(36),
        ForeignKey("employers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=False)
    payment_type = Column(
        Enum(
            PaymentType,
            name="payment_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    source_statement_id = Column(
        String(36),
        ForeignKey("voice_statements.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    worker = relationship("Worker", back_populates="payments")
    employer = relationship("Employer", back_populates="payments")
    source_statement = relationship("VoiceStatement", back_populates="payments")


class VoiceStatement(Base):
    """Voice statement recorded by a worker, with transcript and extracted data."""
    __tablename__ = "voice_statements"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transcript = Column(Text, nullable=True)
    language = Column(String(10), nullable=False, default="hi")
    extracted_data = Column(JSON, nullable=True)
    status = Column(
        Enum(StatementStatus, name="statement_status"),
        nullable=False,
        default=StatementStatus.INITIAL,
    )
    conversation_history = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    worker = relationship("Worker", back_populates="voice_statements")
    work_entries = relationship("WorkEntry", back_populates="source_statement", lazy="selectin")
    payments = relationship("Payment", back_populates="source_statement", lazy="selectin")
    evidence_files = relationship("EvidenceFile", back_populates="statement", lazy="selectin")


class EvidenceFile(Base):
    """Uploaded evidence file (photo, document) linked to a worker / statement."""
    __tablename__ = "evidence_files"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement_id = Column(
        String(36),
        ForeignKey("voice_statements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_reference = Column(String(500), nullable=False)
    document_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    worker = relationship("Worker", back_populates="evidence_files")
    statement = relationship("VoiceStatement", back_populates="evidence_files")
