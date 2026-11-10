"""
Payment endpoints (additional payment-specific operations).
Core CRUD is in the ledger module; this handles payment-specific queries.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.utils.auth import get_current_worker_id

router = APIRouter(prefix="/api/payments", tags=["payments"])


# Payment CRUD is handled via /api/ledger/payments.
# This router exists for any future payment-specific features
# (e.g., payment verification, UPI integration, etc.)
