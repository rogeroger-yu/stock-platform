"""Tests for mean reversion strategy."""

import pandas as pd
import numpy as np
import pytest

from app.strategies.mean_reversion import MeanReversionStrategy, PairsMeanReversionStrategy


@pytest.fixture()
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 100 + np.cumsum(np.random.randn(400) * 0.5)
    close = np.maximum(close, 10)
    return pd.DataFrame({
        "date": dates,
        "open": close * 1.001,
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": np.random.randint(100000, 500000, 400),
    }).set_index("date")


class TestMeanReversion:
    def test_name(self):
        strat = MeanReversionStrategy()
        assert strat.name == "mean_reversion"

    def test_default_params(self):
        strat = MeanReversionStrategy()
        assert strat.params["bb_window"] == 20
        assert strat.params["rsi_period"] == 14
        assert strat.params["min_holding"] == 20

    def test_custom_params(self):
        strat = MeanReversionStrategy(bb_window=30, rsi_lower=25)
        assert strat.params["bb_window"] == 30
        assert strat.params["rsi_lower"] == 25

    def test_signals_length(self, sample_data):
        strat = MeanReversionStrategy(trend_window=50)
        signals = strat.generate_signals(sample_data)
        assert len(signals) == len(sample_data)

    def test_short_data(self):
        strat = MeanReversionStrategy(trend_window=120)
        short = pd.DataFrame({
            "close": [10, 11, 12, 13, 14],
            "open": [10, 11, 12, 13, 14],
            "high": [10, 11, 12, 13, 14],
            "low": [10, 11, 12, 13, 14],
            "volume": [100] * 5,
        })
        signals = strat.generate_signals(short)
        assert (signals == 0).all()

    def test_empty_data(self):
        strat = MeanReversionStrategy()
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        signals = strat.generate_signals(empty)
        assert len(signals) == 0


class TestPairsMeanReversion:
    def test_name(self):
        strat = PairsMeanReversionStrategy()
        assert strat.name == "pairs_mean_reversion"

    def test_signals(self, sample_data):
        strat = PairsMeanReversionStrategy(lookback=30)
        signals = strat.generate_signals(sample_data)
        assert len(signals) == len(sample_data)
