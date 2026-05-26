"""Tests for backtest API and batch ranking — robustly isolated."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np

from app.main import app
from app.db import Base, get_db
from app.models.strategy import Strategy
from app.data import store as data_store


# ─── Shared test DB ─────────────────────────────────────────────────

TEST_DB = "sqlite:///./test_api_shared.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# ─── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True, scope="module")
def setup_app():
    """Set up DB override and create tables for the whole module."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def seed_strategies():
    """Ensure strategies exist for each test."""
    db = TestSession()
    existing = {s.name for s in db.query(Strategy).all()}
    needed = [
        ("test_momentum", "momentum", '{"ma_window": 20, "min_holding": 10}'),
        ("test_macd", "macd", '{"min_holding": 5}'),
        ("test_dual_ma", "dual_ma", '{"fast_window": 5, "slow_window": 20, "min_holding": 5}'),
    ]
    for name, stype, params in needed:
        if name not in existing:
            db.add(Strategy(name=name, strategy_type=stype, params_json=params))
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def seed_sample_data(tmp_path, monkeypatch):
    """Create sample parquet data for test symbols."""
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    for symbol in ["TEST001", "TEST002"]:
        np.random.seed(hash(symbol) % 2**31)
        dates = pd.date_range("2020-01-01", periods=500, freq="B")
        close = 100 + np.cumsum(np.random.randn(500) * 0.5 + 0.05)
        close = np.maximum(close, 10)
        df = pd.DataFrame({
            "date": dates, "open": close, "high": close * 1.005,
            "low": close * 0.995, "close": close,
            "volume": np.random.randint(100000, 500000, 500),
        })
        df.to_parquet(parquet_dir / f"{symbol}.parquet", index=False)
    monkeypatch.setattr(data_store, "PARQUET_DIR", parquet_dir)


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# ─── Backtest API tests ────────────────────────────────────────────


class TestBacktestAPI:
    def test_list_backtests(self, client):
        resp = client.get("/api/backtests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_nonexistent(self, client):
        resp = client.get("/api/backtests/99999")
        assert resp.status_code == 404

    def test_compare_empty(self, client):
        resp = client.post("/api/backtests/compare", json={"backtest_ids": []})
        assert resp.status_code == 200
        assert resp.json() == []


# ─── Batch run tests ───────────────────────────────────────────────


class TestBatchRun:
    def test_batch_run_returns_rankings(self, client):
        resp = client.post("/api/backtests/batch", json={
            "symbols": ["TEST001"],
            "start_date": "2020-06-01",
            "end_date": "2021-12-31",
            "top_n": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data
        assert len(data["rankings"]) == 3
        scores = [r["composite_score"] for r in data["rankings"]]
        assert scores == sorted(scores, reverse=True)

    def test_batch_run_top_n(self, client):
        resp = client.post("/api/backtests/batch", json={
            "symbols": ["TEST001"],
            "start_date": "2020-06-01",
            "end_date": "2021-12-31",
            "top_n": 2,
        })
        assert resp.status_code == 200
        assert len(resp.json()["rankings"]) == 2

    def test_batch_run_multi_stock(self, client):
        resp = client.post("/api/backtests/batch", json={
            "symbols": ["TEST001", "TEST002"],
            "start_date": "2020-06-01",
            "end_date": "2021-12-31",
        })
        assert resp.status_code == 200
        assert len(resp.json()["rankings"]) == 3

    def test_batch_run_no_strategies(self, client):
        db = TestSession()
        all_strats = db.query(Strategy).all()
        for s in all_strats:
            db.delete(s)
        db.commit()

        resp = client.post("/api/backtests/batch", json={
            "symbols": ["TEST001"],
            "start_date": "2020-01-01",
            "end_date": "2021-01-01",
        })
        assert resp.status_code == 400

        # Re-seed
        for name, stype, params in [
            ("test_momentum", "momentum", '{"ma_window": 20, "min_holding": 10}'),
            ("test_macd", "macd", '{"min_holding": 5}'),
            ("test_dual_ma", "dual_ma", '{"fast_window": 5, "slow_window": 20, "min_holding": 5}'),
        ]:
            db.add(Strategy(name=name, strategy_type=stype, params_json=params))
        db.commit()
        db.close()
