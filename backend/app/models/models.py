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
    CheckConstraint,
    Boolean,
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
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
    audit_events = relationship("AuditEvent", back_populates="worker", lazy="selectin")


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
    worksite_id = Column(
        String(36),
        ForeignKey("worksites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    work_date = Column(DateTime(timezone=True), nullable=False)
    days_worked = Column(Numeric(15, 2), nullable=False)
    hours_worked = Column(Numeric(15, 2), nullable=True)
    wage_basis = Column(String(10), nullable=False, default="daily", server_default="daily")
    hourly_rate = Column(Numeric(15, 2), nullable=True)
    overtime_hours = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")
    overtime_multiplier = Column(Numeric(4, 2), nullable=False, default=1.5, server_default="1.5")
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
    worksite = relationship("Worksite", lazy="selectin")
    source_statement = relationship("VoiceStatement", back_populates="work_entries")
    payment_allocations = relationship("PaymentAllocation", back_populates="work_entry", lazy="selectin")
    __table_args__ = (
        CheckConstraint("wage_basis IN ('daily', 'hourly')", name="ck_work_entries_wage_basis_allowed"),
        CheckConstraint("hourly_rate IS NULL OR hourly_rate > 0", name="ck_work_entries_hourly_rate_positive"),
        CheckConstraint("overtime_hours >= 0", name="ck_work_entries_overtime_non_negative"),
        CheckConstraint("overtime_multiplier >= 1 AND overtime_multiplier <= 3", name="ck_work_entries_overtime_multiplier"),
    )


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
    allocations = relationship("PaymentAllocation", back_populates="payment", lazy="selectin")


class PaymentAllocation(Base):
    """A transparent partial allocation of a received payment to work owed."""
    __tablename__ = "payment_allocations"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id = Column(
        String(36), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_entry_id = Column(
        String(36), ForeignKey("work_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    worker = relationship("Worker")
    payment = relationship("Payment", back_populates="allocations")
    work_entry = relationship("WorkEntry", back_populates="payment_allocations")
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_allocations_positive_amount"),)


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
    file_name = Column(String(255), nullable=True)
    document_type = Column(String(100), nullable=True)
    content_type = Column(String(127), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    consent_given = Column(Boolean, nullable=False, default=False, server_default="false")
    work_entry_id = Column(String(36), ForeignKey("work_entries.id", ondelete="SET NULL"), nullable=True)
    payment_id = Column(String(36), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    worker = relationship("Worker", back_populates="evidence_files")
    statement = relationship("VoiceStatement", back_populates="evidence_files")


class AuditEvent(Base):
    """Append-only event log for worker-owned records and voice workflow changes."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(
        String(36),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(80), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(36), nullable=False)
    source_statement_id = Column(
        String(36),
        ForeignKey("voice_statements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    worker = relationship("Worker", back_populates="audit_events")
    __table_args__ = (
        Index("ix_audit_events_worker_created", "worker_id", "created_at"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
    )


class Worksite(Base):
    """A worker-owned site, optionally associated with a recorded employer."""
    __tablename__ = "worksites"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(String(36), ForeignKey("employers.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class WageAgreement(Base):
    """Worker-reported wage terms with an explicit employer and effective period."""
    __tablename__ = "wage_agreements"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    employer_id = Column(String(36), ForeignKey("employers.id", ondelete="CASCADE"), nullable=False, index=True)
    worksite_id = Column(String(36), ForeignKey("worksites.id", ondelete="SET NULL"), nullable=True, index=True)
    wage_basis = Column(String(10), nullable=False)
    daily_rate = Column(Numeric(15, 2), nullable=True)
    hourly_rate = Column(Numeric(15, 2), nullable=True)
    overtime_multiplier = Column(Numeric(4, 2), nullable=False, default=1.5, server_default="1.5")
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    terms = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint("wage_basis IN ('daily', 'hourly')", name="ck_wage_agreements_basis_allowed"),
        CheckConstraint("daily_rate IS NULL OR daily_rate > 0", name="ck_wage_agreements_daily_rate_positive"),
        CheckConstraint("hourly_rate IS NULL OR hourly_rate > 0", name="ck_wage_agreements_hourly_rate_positive"),
        CheckConstraint("overtime_multiplier >= 1 AND overtime_multiplier <= 3", name="ck_wage_agreements_overtime_multiplier"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_wage_agreements_effective_period"),
        CheckConstraint("(wage_basis = 'daily' AND daily_rate IS NOT NULL) OR (wage_basis = 'hourly' AND hourly_rate IS NOT NULL)", name="ck_wage_agreements_rate_matches_basis"),
    )


class WageCalculation(Base):
    """Immutable Decimal calculation snapshot for explaining a work record."""
    __tablename__ = "wage_calculations"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    work_entry_id = Column(String(36), ForeignKey("work_entries.id", ondelete="CASCADE"), nullable=False, unique=True)
    base_amount = Column(Numeric(15, 2), nullable=False)
    overtime_amount = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    formula_version = Column(String(30), nullable=False, default="decimal-v1", server_default="decimal-v1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    __table_args__ = (
        CheckConstraint("base_amount >= 0 AND overtime_amount >= 0 AND total_amount >= 0", name="ck_wage_calculations_non_negative"),
    )


class WorkerPreference(Base):
    """One-to-one product, privacy, and accessibility preferences."""
    __tablename__ = "worker_preferences"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True)
    theme = Column(String(10), nullable=False, default="system", server_default="system")
    audio_retention_consent = Column(Boolean, nullable=False, default=False, server_default="false")
    voice_response_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata", server_default="Asia/Kolkata")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    __table_args__ = (CheckConstraint("theme IN ('light', 'dark', 'system')", name="ck_worker_preferences_theme"),)


class VoiceGenerationHistory(Base):
    """Consent-aware metadata for generated speech; audio is stored only by reference."""
    __tablename__ = "voice_generation_history"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    source_statement_id = Column(String(36), ForeignKey("voice_statements.id", ondelete="SET NULL"), nullable=True)
    text_input = Column(Text, nullable=False)
    language = Column(String(20), nullable=False)
    model_id = Column(String(60), nullable=False)
    voice_id = Column(String(100), nullable=False)
    status = Column(String(12), nullable=False)
    latency_ms = Column(Numeric(10, 0), nullable=True)
    audio_reference = Column(String(500), nullable=True)
    audio_retention_consent = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    __table_args__ = (
        CheckConstraint("status IN ('success', 'failed')", name="ck_voice_generation_status"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_voice_generation_latency_non_negative"),
    )


class ReminderPreference(Base):
    """Explicit worker consent and cadence preferences for in-app reminders."""
    __tablename__ = "reminder_preferences"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, unique=True)
    consent_given = Column(Boolean, nullable=False, default=False, server_default="false")
    daily_work_entry = Column(Boolean, nullable=False, default=False, server_default="false")
    unconfirmed_record = Column(Boolean, nullable=False, default=False, server_default="false")
    weekly_summary = Column(Boolean, nullable=False, default=False, server_default="false")
    monthly_statement = Column(Boolean, nullable=False, default=False, server_default="false")
    payment_follow_up = Column(Boolean, nullable=False, default=False, server_default="false")
    reminder_time = Column(String(5), nullable=False, default="18:00", server_default="18:00")
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata", server_default="Asia/Kolkata")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class Reminder(Base):
    """A worker-scoped reminder record with explicit lifecycle state."""
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_type = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(12), nullable=False, default="pending", server_default="pending")
    source_record_id = Column(String(36), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'delivered', 'dismissed')", name="ck_reminders_status"),
        Index("ix_reminders_worker_schedule", "worker_id", "scheduled_at"),
    )


class SavingsGoal(Base):
    """Worker-entered target amount and date, separate from computed ledger totals."""
    __tablename__ = "savings_goals"

    id = Column(String(36), primary_key=True, default=_uuid)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)
    target_date = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    __table_args__ = (CheckConstraint("target_amount > 0", name="ck_savings_goals_target_positive"),)
