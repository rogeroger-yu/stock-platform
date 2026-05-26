"""Tests for backtest-to-trade bridge."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np

from app.db import Base, get_db
from app.paper_trade.engine import PaperTradeEngine
from app.paper_trade.bridge import BacktestTradeBridge
from app.data import store as data_store


@pytest.fixture()
def paper_engine():
    return PaperTradeEngine(initial_capital=1_000_000.0)


@pytest.fixture()
def bridge(paper_engine):
    return BacktestTradeBridge(paper_engine)


@pytest.fixture(autouse=True)
def seed_data(tmp_path, monkeypatch):
    """Create sample data for tests."""
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    close = 100 + np.cumsum(np.random.randn(500) * 0.5 + 0.05)
    close = np.maximum(close, 10)
    df = pd.DataFrame({
        "date": dates, "open": close, "high": close * 1.005,
        "low": close * 0.995, "close": close,
        "volume": np.random.randint(100000, 500000, 500),
    })
    df.to_parquet(parquet_dir / "TEST001.parquet", index=False)
    monkeypatch.setattr(data_store, "PARQUET_DIR", parquet_dir)


class TestBridgeActivation:
    def test_activate_strategy(self, bridge):
        result = bridge.activate_strategy("momentum", {"ma_window": 20}, ["TEST001"])
        assert result["status"] == "activated"
        assert len(bridge.get_active_strategies()) == 1

    def test_activate_unknown_type(self, bridge):
        result = bridge.activate_strategy("nonexistent_xyz", {}, ["TEST001"])
        assert "error" in result

    def test_deactivate_strategy(self, bridge):
        bridge.activate_strategy("momentum", {}, ["TEST001"])
        bridge.activate_strategy("macd", {}, ["TEST001"])
        assert len(bridge.get_active_strategies()) == 2

        result = bridge.deactivate_strategy("momentum")
        assert result["removed"] == 1
        assert len(bridge.get_active_strategies()) == 1

    def test_multiple_symbols(self, bridge):
        result = bridge.activate_strategy("dual_ma", {"fast_window": 5}, ["TEST001"])
        assert result["status"] == "activated"


class TestDailyCheck:
    def test_check_with_no_strategies(self, bridge):
        result = bridge.run_daily_check()
        assert result["checked"] == 0

    def test_check_with_active_strategy(self, bridge):
        bridge.activate_strategy("momentum", {"ma_window": 20, "min_holding": 10}, ["TEST001"])
        result = bridge.run_daily_check()
        assert result["checked"] == 1
        assert "signals" in result
        assert "orders_suggested" in result

    def test_check_with_macd(self, bridge):
        bridge.activate_strategy("macd", {"min_holding": 5}, ["TEST001"])
        result = bridge.run_daily_check()
        assert result["checked"] == 1


class TestSignalHistory:
    def test_history_accumulates(self, bridge):
        bridge.activate_strategy("momentum", {"ma_window": 20}, ["TEST001"])
        bridge.run_daily_check()
        bridge.run_daily_check()
        history = bridge.get_signal_history()
        assert len(history) >= 1  # At least some records

    def test_history_limit(self, bridge):
        bridge.activate_strategy("momentum", {"ma_window": 20}, ["TEST001"])
        for _ in range(5):
            bridge.run_daily_check()
        history = bridge.get_signal_history(limit=3)
        assert len(history) <= 3


class TestBacktestVsLive:
    def test_comparison(self, bridge, paper_engine):
        # Execute some paper trades first
        paper_engine.place_order(
            "TEST001",
            __import__("app.paper_trade.engine", fromlist=["OrderSide"]).OrderSide.BUY,
            100, 100.0
        )

        result = bridge.backtest_vs_live(
            "momentum", {"ma_window": 20, "min_holding": 10}, ["TEST001"]
        )
        assert "backtest_metrics" in result
        assert "paper_account" in result
        assert "paper_trades_count" in result
