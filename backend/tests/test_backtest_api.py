import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_run_backtest_returns_pending():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/backtest/run",
            json={
                "strategy": "test",
                "params": {},
                "start_date": "2015-01-01",
                "end_date": "2024-12-31",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_backtest_by_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create one first
        create_resp = await client.post(
            "/api/backtest/run",
            json={"strategy": "momentum", "params": {"window": 20}},
        )
        bt_id = create_resp.json()["id"]

        # Fetch it
        resp = await client.get(f"/api/backtest/{bt_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_name"] == "momentum"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_backtest_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/backtest/99999")
    assert resp.status_code == 404
