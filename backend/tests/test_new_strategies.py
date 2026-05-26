"""Tests for new strategy implementations (open-source collection)."""

import pandas as pd
import numpy as np
import pytest

from app.strategies.macd import MACDStrategy, MACDHistogramStrategy
from app.strategies.bollinger_breakout import BollingerBreakoutStrategy, BollingerSqueezeStrategy
from app.strategies.kdj import KDJStrategy, KDJReversalStrategy
from app.strategies.turtle import TurtleStrategy, TurtleSystem2Strategy
from app.strategies.dual_ma import DualMAStrategy, TripleMAStrategy
from app.strategies.registry import get_strategy_class, list_strategy_types


# ─── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture()
def uptrend_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 100 + np.cumsum(np.random.randn(400) * 0.5 + 0.12)
    close = np.maximum(close, 10)
    return pd.DataFrame({
        "date": dates, "open": close * 1.001, "high": close * 1.005,
        "low": close * 0.995, "close": close,
        "volume": np.random.randint(100000, 500000, 400),
    }).set_index("date")


@pytest.fixture()
def downtrend_data():
    np.random.seed(123)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 200 + np.cumsum(np.random.randn(400) * 0.5 - 0.12)
    close = np.maximum(close, 10)
    return pd.DataFrame({
        "date": dates, "open": close * 1.001, "high": close * 1.005,
        "low": close * 0.995, "close": close,
        "volume": np.random.randint(100000, 500000, 400),
    }).set_index("date")


@pytest.fixture()
def sideways_data():
    np.random.seed(99)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    close = 100 + np.sin(np.arange(400) * 0.05) * 10 + np.random.randn(400) * 0.5
    return pd.DataFrame({
        "date": dates, "open": close * 1.001, "high": close * 1.005,
        "low": close * 0.995, "close": close,
        "volume": np.random.randint(100000, 500000, 400),
    }).set_index("date")


# ─── Helper ─────────────────────────────────────────────────────────


def _assert_strategy_works(strategy, data):
    """Common assertions for any strategy."""
    signals = strategy.generate_signals(data)
    assert len(signals) == len(data)
    assert set(signals.unique()).issubset({-1, 0, 1})
    # Should have at least some signals in 400 days of data
    return signals


# ─── MACD ───────────────────────────────────────────────────────────


class TestMACDStrategy:
    def test_name(self):
        assert MACDStrategy().name == "macd"

    def test_params_override(self):
        s = MACDStrategy(fast_period=10, slow_period=20)
        assert s.params["fast_period"] == 10
        assert s.params["slow_period"] == 20

    def test_uptrend_signals(self, uptrend_data):
        s = MACDStrategy(min_holding=5)
        signals = _assert_strategy_works(s, uptrend_data)
        assert (signals == 1).sum() > 0

    def test_downtrend_signals(self, downtrend_data):
        s = MACDStrategy(min_holding=5)
        _assert_strategy_works(s, downtrend_data)

    def test_zero_filter(self, uptrend_data):
        s_no = MACDStrategy(use_zero_filter=False, min_holding=5)
        s_yes = MACDStrategy(use_zero_filter=True, min_holding=5)
        assert (s_yes.generate_signals(uptrend_data) == 1).sum() <= \
               (s_no.generate_signals(uptrend_data) == 1).sum()


class TestMACDHistogram:
    def test_name(self):
        assert MACDHistogramStrategy().name == "macd_histogram"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(MACDHistogramStrategy(), uptrend_data)


# ─── Bollinger ──────────────────────────────────────────────────────


class TestBollingerBreakout:
    def test_name(self):
        assert BollingerBreakoutStrategy().name == "bollinger_breakout"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(BollingerBreakoutStrategy(), uptrend_data)

    def test_empty_data(self):
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        signals = BollingerBreakoutStrategy().generate_signals(empty)
        assert len(signals) == 0


class TestBollingerSqueeze:
    def test_name(self):
        assert BollingerSqueezeStrategy().name == "bollinger_squeeze"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(BollingerSqueezeStrategy(), uptrend_data)


# ─── KDJ ────────────────────────────────────────────────────────────


class TestKDJStrategy:
    def test_name(self):
        assert KDJStrategy().name == "kdj"

    def test_default_params(self):
        s = KDJStrategy()
        assert s.params["n"] == 9
        assert s.params["oversold"] == 20

    def test_uptrend_signals(self, uptrend_data):
        s = KDJStrategy(min_holding=5)
        signals = _assert_strategy_works(s, uptrend_data)
        assert (signals == 1).sum() > 0

    def test_downtrend_signals(self, downtrend_data):
        _assert_strategy_works(KDJStrategy(min_holding=5), downtrend_data)

    def test_sideways_signals(self, sideways_data):
        _assert_strategy_works(KDJStrategy(min_holding=5), sideways_data)


class TestKDJReversal:
    def test_name(self):
        assert KDJReversalStrategy().name == "kdj_reversal"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(KDJReversalStrategy(), uptrend_data)


# ─── Turtle ─────────────────────────────────────────────────────────


class TestTurtleStrategy:
    def test_name(self):
        assert TurtleStrategy().name == "turtle"

    def test_default_params(self):
        s = TurtleStrategy()
        assert s.params["entry_window"] == 20
        assert s.params["exit_window"] == 10

    def test_uptrend_signals(self, uptrend_data):
        _assert_strategy_works(TurtleStrategy(min_holding=5), uptrend_data)

    def test_downtrend_signals(self, downtrend_data):
        _assert_strategy_works(TurtleStrategy(min_holding=5), downtrend_data)


class TestTurtleSystem2:
    def test_name(self):
        assert TurtleSystem2Strategy().name == "turtle_system2"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(TurtleSystem2Strategy(), uptrend_data)


# ─── Dual MA ────────────────────────────────────────────────────────


class TestDualMAStrategy:
    def test_name(self):
        assert DualMAStrategy().name == "dual_ma"

    def test_default_params(self):
        s = DualMAStrategy()
        assert s.params["fast_window"] == 10
        assert s.params["slow_window"] == 30

    def test_uptrend_signals(self, uptrend_data):
        s = DualMAStrategy(min_holding=5)
        signals = _assert_strategy_works(s, uptrend_data)
        assert (signals == 1).sum() > 0

    def test_ema_type(self, uptrend_data):
        s = DualMAStrategy(ma_type="ema", min_holding=5)
        _assert_strategy_works(s, uptrend_data)

    def test_sma_type(self, uptrend_data):
        s = DualMAStrategy(ma_type="sma", min_holding=5)
        _assert_strategy_works(s, uptrend_data)

    def test_rsi_filter(self, uptrend_data):
        s = DualMAStrategy(use_rsi_filter=True, rsi_upper=50, min_holding=5)
        _assert_strategy_works(s, uptrend_data)


class TestTripleMAStrategy:
    def test_name(self):
        assert TripleMAStrategy().name == "triple_ma"

    def test_signals(self, uptrend_data):
        _assert_strategy_works(TripleMAStrategy(min_holding=5), uptrend_data)


# ─── Registry ───────────────────────────────────────────────────────


class TestRegistry:
    def test_list_all_types(self):
        types = list_strategy_types()
        assert len(types) >= 15  # 15 strategy variants
        type_keys = [t["type"] for t in types]
        assert "momentum" in type_keys
        assert "macd" in type_keys
        assert "turtle" in type_keys
        assert "dual_ma" in type_keys
        assert "kdj" in type_keys

    def test_get_known_strategy(self):
        cls = get_strategy_class("macd")
        assert cls is not None
        assert cls().name == "macd"

    def test_get_unknown_strategy(self):
        cls = get_strategy_class("nonexistent_xyz")
        assert cls is None

    def test_all_types_have_default_params(self):
        types = list_strategy_types()
        for t in types:
            assert "default_params" in t
            assert isinstance(t["default_params"], dict)
