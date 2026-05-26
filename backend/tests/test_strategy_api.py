"""Tests for strategy CRUD API (persistent strategies)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db


# ─── Test DB setup ──────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_strategies.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
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
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# ─── Tests ──────────────────────────────────────────────────────────


class TestStrategyCRUD:
    def test_create_strategy(self, client):
        resp = client.post("/api/strategies", json={
            "name": "My Momentum",
            "strategy_type": "momentum",
            "description": "Test strategy",
            "params": {"ma_window": 40, "min_holding": 15},
            "symbols": ["000001", "600519"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Momentum"
        assert data["strategy_type"] == "momentum"
        assert data["params"]["ma_window"] == 40
        assert data["id"] > 0

    def test_create_duplicate_name(self, client):
        client.post("/api/strategies", json={
            "name": "DupTest", "strategy_type": "momentum"
        })
        resp = client.post("/api/strategies", json={
            "name": "DupTest", "strategy_type": "macd"
        })
        assert resp.status_code == 409

    def test_list_strategies(self, client):
        resp = client.get("/api/strategies")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_strategy(self, client):
        r = client.post("/api/strategies", json={"name": "GetTest", "strategy_type": "turtle"})
        sid = r.json()["id"]
        resp = client.get(f"/api/strategies/{sid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetTest"

    def test_update_strategy(self, client):
        r = client.post("/api/strategies", json={
            "name": "UpdTest", "strategy_type": "kdj", "params": {"n": 9}
        })
        sid = r.json()["id"]
        resp = client.put(f"/api/strategies/{sid}", json={
            "params": {"n": 14, "oversold": 25},
            "description": "Updated KDJ"
        })
        assert resp.status_code == 200
        assert resp.json()["params"]["n"] == 14
        assert resp.json()["description"] == "Updated KDJ"

    def test_update_name(self, client):
        r = client.post("/api/strategies", json={"name": "OldName", "strategy_type": "macd"})
        sid = r.json()["id"]
        resp = client.put(f"/api/strategies/{sid}", json={"name": "NewName"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewName"

    def test_delete_strategy(self, client):
        r = client.post("/api/strategies", json={"name": "DelTest", "strategy_type": "momentum"})
        sid = r.json()["id"]
        resp = client.delete(f"/api/strategies/{sid}")
        assert resp.status_code == 200
        resp = client.get(f"/api/strategies/{sid}")
        assert resp.status_code == 404

    def test_filter_by_type(self, client):
        resp = client.get("/api/strategies?strategy_type=macd")
        assert resp.status_code == 200
        for s in resp.json():
            assert s["strategy_type"] == "macd"

    def test_seed_defaults(self, client):
        resp = client.post("/api/strategies/seed-defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 15

        # Second call should skip all
        resp2 = client.post("/api/strategies/seed-defaults")
        assert len(resp2.json()["skipped"]) >= 15
