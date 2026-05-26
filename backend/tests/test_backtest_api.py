"""Tests for backtest API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_run_backtest_returns_result():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/backtests/run",
            json={
                "strategy_id": "test",
                "start_date": "2015-01-01",
                "end_date": "2024-12-31",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "strategy_id" in data
    assert "total_return" in data
    assert "sharpe_ratio" in data


@pytest.mark.asyncio
async def test_run_backtest_with_params():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/backtests/run",
            json={
                "strategy_id": "momentum",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "initial_capital": 500000,
                "commission": 0.002,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_id"] == "momentum"
