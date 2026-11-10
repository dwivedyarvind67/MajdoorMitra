"""
Shared test fixtures for MazdoorMitra backend tests.
Uses an in-memory SQLite database with StaticPool for full isolation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.main import app
from app.models.models import Worker, Employer
from app.utils.auth import create_access_token, hash_pin
from app.config import settings


@pytest.fixture(autouse=True)
def test_jwt_secret(monkeypatch):
    """Use a fixture-only signing key; never depend on a copied local secret."""
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "unit-test-signing-key-with-more-than-32-characters")


# ---------------------------------------------------------------------------
# Database engine & session (function-scoped for isolation)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory SQLite engine with StaticPool for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a fresh async session for each test."""
    session_factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Test worker & employer
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_worker(db_session: AsyncSession):
    """Insert and return a test worker."""
    worker = Worker(
        id=str(uuid.uuid4()),
        name="Test Worker",
        phone="9876543210",
        preferred_language="hi",
        pin_hash=hash_pin("1234"),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)
    return worker


@pytest_asyncio.fixture
async def test_employer(db_session: AsyncSession, test_worker: Worker):
    """Insert and return a test employer."""
    employer = Employer(
        id=str(uuid.uuid4()),
        worker_id=test_worker.id,
        name="Test Contractor",
        contact_details="9999999999",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(employer)
    await db_session.commit()
    await db_session.refresh(employer)
    return employer


@pytest_asyncio.fixture
def auth_token(test_worker: Worker) -> str:
    """Generate a JWT token for the test worker."""
    return create_access_token({"sub": test_worker.id})


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_engine):
    """Provide an async HTTP test client with the test database."""
    session_factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
