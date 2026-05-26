"""Tests for portfolio engine v1 — multi-stock portfolio backtesting."""

import pandas as pd
import numpy as np
import pytest

from app.core.portfolio import PortfolioEngine, PortfolioResult
from app.core.strategy_base import StrategyBase


class MomentumStrategy(StrategyBase):
    """Simple momentum: buy if price > N-day MA, sell otherwise."""

    def __init__(self, window: int = 20):
        self._window = window

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def params(self) -> dict:
        return {"window": self._window}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        ma = data["close"].rolling(window=self._window).mean()
        signals = pd.Series(0, index=data.index)
        signals[data["close"] > ma] = 1
        signals[data["close"] <= ma] = -1
        return signals


@pytest.fixture()
def multi_stock_data():
    """Generate synthetic data for 3 stocks."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")

    def make_stock(drift):
        close = 100 + np.cumsum(np.random.randn(500) * 0.5 + drift)
        close = np.maximum(close, 10)
        return pd.DataFrame({
            "date": dates,
            "open": close * 1.001,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.randint(100000, 500000, 500),
        })

    return {
        "AAPL": make_stock(0.05),
        "GOOG": make_stock(0.03),
        "MSFT": make_stock(0.04),
    }


class TestPortfolioEngine:
    def test_basic_run(self, multi_stock_data):
        engine = PortfolioEngine(initial_capital=1_000_000)
        strategy = MomentumStrategy(window=20)
        result = engine.run(strategy, multi_stock_data)

        assert isinstance(result, PortfolioResult)
        assert result.strategy_name == "momentum"
        assert result.symbols == ["AAPL", "GOOG", "MSFT"]
        assert len(result.equity_curve) > 0
        assert result.num_trades > 0

    def test_empty_data(self):
        engine = PortfolioEngine()
        strategy = MomentumStrategy()
        result = engine.run(strategy, {})

        assert result.total_return == 0.0
        assert result.num_trades == 0

    def test_single_stock(self, multi_stock_data):
        engine = PortfolioEngine()
        strategy = MomentumStrategy()
        single = {"AAPL": multi_stock_data["AAPL"]}
        result = engine.run(strategy, single)

        assert result.num_trades > 0
        assert "AAPL" in result.stock_returns

    def test_commission_impact(self, multi_stock_data):
        strat = MomentumStrategy(window=20)

        engine_free = PortfolioEngine(commission=0.0, slippage=0.0)
        result_free = engine_free.run(strat, multi_stock_data)

        engine_paid = PortfolioEngine(commission=0.001, slippage=0.0005)
        result_paid = engine_paid.run(strat, multi_stock_data)

        assert result_paid.total_return < result_free.total_return

    def test_to_dict(self, multi_stock_data):
        engine = PortfolioEngine()
        strategy = MomentumStrategy()
        result = engine.run(strategy, multi_stock_data)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "equity_curve" in d
        assert "stock_returns" in d
        assert len(d["stock_returns"]) == 3

    def test_metrics_reasonable(self, multi_stock_data):
        engine = PortfolioEngine()
        strategy = MomentumStrategy(window=30)
        result = engine.run(strategy, multi_stock_data)

        assert -5 < result.sharpe < 5
        assert 0 <= result.max_drawdown <= 1
        assert 0 <= result.win_rate <= 1
