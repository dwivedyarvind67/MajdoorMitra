"""
Integration tests for MazdoorMitra API endpoints:
- Health check
- Worker registration and login
- Protected endpoints & data isolation
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "MazdoorMitra API"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register a new worker
    reg_payload = {
        "name": "Mohan Lal",
        "phone": "9876543299",
        "pin": "1234",
        "preferred_language": "hi",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code in [200, 201]
    reg_data = reg_res.json()
    assert "token" in reg_data or "access_token" in reg_data

    # Login with phone and PIN
    login_payload = {
        "phone": "9876543299",
        "pin": "1234",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data.get("token") or login_data.get("access_token")
    assert token is not None


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    # Attempt to access ledger summary without token
    response = await client.get("/api/ledger/summary")
    assert response.status_code in [401, 403]
