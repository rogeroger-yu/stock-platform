import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_run_backtest_stub():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/backtests/run",
            json={
                "strategy_id": "test-strat",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_id"] == "test-strat"
    assert "total_return" in data
