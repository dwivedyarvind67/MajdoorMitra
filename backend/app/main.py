"""
MazdoorMitra FastAPI application entry point.
Configures CORS, includes all routers, and manages app lifecycle.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.connection import init_db

# Import all routers
from app.api.auth import router as auth_router
from app.api.voice import router as voice_router
from app.api.ledger import router as ledger_router
from app.api.payments import router as payments_router
from app.api.employers import router as employers_router
from app.api.statements import router as statements_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: create tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title="MazdoorMitra API",
    description="Voice-first wage tracking platform for Indian daily-wage workers.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(voice_router)
app.include_router(ledger_router)
app.include_router(payments_router)
app.include_router(employers_router)
app.include_router(statements_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MazdoorMitra API", "version": "1.0.0"}
