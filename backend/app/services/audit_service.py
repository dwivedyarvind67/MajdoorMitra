"""Append worker-scoped audit events in the same database transaction as changes."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditEvent


class AuditService:
    """Create immutable event snapshots without duplicating full record contents."""

    @staticmethod
    def record(
        session: AsyncSession,
        worker_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        *,
        source_statement_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            worker_id=worker_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            source_statement_id=source_statement_id,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        session.add(event)
        return event
