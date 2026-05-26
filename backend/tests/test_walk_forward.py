"""Tests for walk-forward framework."""

import pandas as pd
import numpy as np
import pytest

from app.core.walk_forward import (
    walk_forward_single,
    walk_forward_portfolio,
    WFResult,
    WFBenchmark,
)
from app.strategies.momentum import MomentumStrategy


@pytest.fixture()
def synthetic_data():
    """Generate 10 years of synthetic daily data."""
    np.random.seed(42)
    dates = pd.date_range("2015-01-01", periods=2500, freq="B")
    close = 100 + np.cumsum(np.random.randn(2500) * 0.5 + 0.02)
    close = np.maximum(close, 10)
    return pd.DataFrame({
        "date": dates,
        "open": close * 1.001,
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": np.random.randint(100000, 500000, 2500),
    })


@pytest.fixture()
def multi_stock_data():
    np.random.seed(42)
    dates = pd.date_range("2015-01-01", periods=2500, freq="B")

    def make(drift):
        close = 100 + np.cumsum(np.random.randn(2500) * 0.5 + drift)
        close = np.maximum(close, 10)
        return pd.DataFrame({
            "date": dates,
            "open": close * 1.001,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.randint(100000, 500000, 2500),
        })

    return {"STOCK_A": make(0.03), "STOCK_B": make(0.04)}


class TestWalkForwardSingle:
    def test_basic_run(self, synthetic_data):
        param_grid = {"ma_window": [20, 40], "min_holding": [20]}
        result = walk_forward_single(
            MomentumStrategy,
            param_grid,
            synthetic_data,
            is_start="2015-01-01",
            is_end="2020-12-31",
            oos_start="2021-01-01",
            oos_end="2024-12-31",
        )

        assert isinstance(result, WFResult)
        assert result.strategy_name == "MomentumStrategy"
        assert result.param_grid_size == 2
        assert result.best_params != {}
        assert "sharpe" in result.is_result
        assert "sharpe" in result.oos_result

    def test_returns_result_dict(self, synthetic_data):
        param_grid = {"ma_window": [20]}
        result = walk_forward_single(
            MomentumStrategy, param_grid, synthetic_data
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "oos_annualized_return" in d

    def test_empty_data(self):
        empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        result = walk_forward_single(
            MomentumStrategy, {"ma_window": [20]}, empty
        )
        assert result.param_grid_size == 0


class TestWalkForwardPortfolio:
    def test_basic_run(self, multi_stock_data):
        param_grid = {"ma_window": [20], "min_holding": [20]}
        result = walk_forward_portfolio(
            MomentumStrategy,
            param_grid,
            multi_stock_data,
        )

        assert isinstance(result, WFResult)
        assert result.strategy_name == "MomentumStrategy"


class TestBenchmark:
    def test_target_met(self):
        bench = WFBenchmark(min_annualized_return=0.6, max_drawdown=0.3, min_sharpe=1.5)
        assert bench.check(0.7, 0.2, 2.0) == True

    def test_target_not_met_return(self):
        bench = WFBenchmark(min_annualized_return=0.6, max_drawdown=0.3, min_sharpe=1.5)
        assert bench.check(0.3, 0.2, 2.0) == False

    def test_target_not_met_drawdown(self):
        bench = WFBenchmark(min_annualized_return=0.6, max_drawdown=0.3, min_sharpe=1.5)
        assert bench.check(0.7, 0.5, 2.0) == False

    def test_target_not_met_sharpe(self):
        bench = WFBenchmark(min_annualized_return=0.6, max_drawdown=0.3, min_sharpe=1.5)
        assert bench.check(0.7, 0.2, 0.5) == False
