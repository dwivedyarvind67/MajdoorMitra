"""
Authentication endpoints: register and login.
PIN-based authentication for workers with limited digital literacy.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.models import Worker
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.utils.auth import create_access_token, hash_pin, verify_pin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new worker with phone and PIN."""
    # Check if phone already exists
    stmt = select(Worker).where(Worker.phone == request.phone)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A worker with this phone number is already registered.",
        )

    worker = Worker(
        id=str(uuid.uuid4()),
        name=request.name,
        phone=request.phone,
        preferred_language=request.preferred_language,
        pin_hash=hash_pin(request.pin),
        created_at=datetime.now(timezone.utc),
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    token = create_access_token({"sub": worker.id})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        worker_id=worker.id,
        name=worker.name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with phone and PIN."""
    stmt = select(Worker).where(Worker.phone == request.phone)
    result = await db.execute(stmt)
    worker = result.scalar_one_or_none()

    if not worker or not verify_pin(request.pin, worker.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or PIN.",
        )

    token = create_access_token({"sub": worker.id})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        worker_id=worker.id,
        name=worker.name,
    )
