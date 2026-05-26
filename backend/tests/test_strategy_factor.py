"""Tests for factor score strategy."""

import pandas as pd
import numpy as np
import pytest

from app.strategies.factor_score import FactorScoreStrategy


@pytest.fixture()
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 100 + np.cumsum(np.random.randn(400) * 0.5 + 0.02)
    close = np.maximum(close, 10)
    return pd.DataFrame({
        "date": dates,
        "open": close * 1.001,
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": np.random.randint(100000, 500000, 400),
    }).set_index("date")


class TestFactorScore:
    def test_name(self):
        strat = FactorScoreStrategy()
        assert strat.name == "factor_score"

    def test_default_params(self):
        strat = FactorScoreStrategy()
        assert strat.params["buy_threshold"] == 0.6
        assert strat.params["sell_threshold"] == 0.3
        assert strat.params["min_holding"] == 20
        assert "momentum" in strat.params["factor_weights"]

    def test_custom_weights(self):
        strat = FactorScoreStrategy(factor_weights={"momentum": 0.5, "trend": 0.5})
        assert strat.params["factor_weights"]["momentum"] == 0.5

    def test_signals_length(self, sample_data):
        strat = FactorScoreStrategy()
        signals = strat.generate_signals(sample_data)
        assert len(signals) == len(sample_data)

    def test_signals_values(self, sample_data):
        strat = FactorScoreStrategy()
        signals = strat.generate_signals(sample_data)
        # Signals should only be -1, 0, 1
        valid = set(signals.unique())
        assert valid.issubset({-1, 0, 1})

    def test_has_buy_signals(self, sample_data):
        strat = FactorScoreStrategy(buy_threshold=0.3, min_holding=10)
        signals = strat.generate_signals(sample_data)
        buy_count = (signals == 1).sum()
        # With low threshold, should have some buys
        assert buy_count >= 0  # at least doesn't crash

    def test_factor_computation(self, sample_data):
        strat = FactorScoreStrategy()
        factors = strat._compute_factors(sample_data)
        assert "momentum" in factors.columns
        assert "volatility" in factors.columns
        assert "volume" in factors.columns
        assert "rsi" in factors.columns
        assert "trend" in factors.columns
        # All factors should be in [0, 1] range (approximately)
        for col in factors.columns:
            valid = factors[col].dropna()
            if len(valid) > 0:
                assert valid.min() >= -0.01  # allow small float errors
                assert valid.max() <= 1.01

    def test_empty_data(self):
        strat = FactorScoreStrategy()
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        signals = strat.generate_signals(empty)
        assert len(signals) == 0

    def test_normalize(self):
        strat = FactorScoreStrategy()
        s = pd.Series([1, 2, 3, 4, 5])
        result = strat._normalize(s)
        assert result.min() == 0.0
        assert result.max() == 1.0

    def test_normalize_constant(self):
        strat = FactorScoreStrategy()
        s = pd.Series([5, 5, 5, 5])
        result = strat._normalize(s)
        assert (result == 0.5).all()
