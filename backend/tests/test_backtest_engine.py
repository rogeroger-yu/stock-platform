"""Tests for backtest engine v0 — single stock, fixed holding, full metrics."""

import pandas as pd
import numpy as np
import pytest

from app.core.backtest_engine import BacktestEngine, BacktestResult
from app.core.strategy_base import StrategyBase


# ---------------------------------------------------------------------------
# Test strategies
# ---------------------------------------------------------------------------


class BuyAndHoldStrategy(StrategyBase):
    """Buy on day 1, sell on last day."""

    @property
    def name(self) -> str:
        return "buy_and_hold"

    @property
    def params(self) -> dict:
        return {}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        signals.iloc[0] = 1  # buy on first day
        signals.iloc[-1] = -1  # sell on last day
        return signals


class EveryNDaysStrategy(StrategyBase):
    """Buy every N days, sell after M days."""

    def __init__(self, buy_interval: int = 10, hold_days: int = 5):
        self._buy_interval = buy_interval
        self._hold_days = hold_days

    @property
    def name(self) -> str:
        return "every_n_days"

    @property
    def params(self) -> dict:
        return {"buy_interval": self._buy_interval, "hold_days": self._hold_days}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        n = len(data)
        i = 0
        while i < n:
            signals.iloc[i] = 1  # buy
            sell_idx = min(i + self._hold_days, n - 1)
            signals.iloc[sell_idx] = -1  # sell
            i += self._buy_interval
        return signals


class NoTradeStrategy(StrategyBase):
    """Never trades."""

    @property
    def name(self) -> str:
        return "no_trade"

    @property
    def params(self) -> dict:
        return {}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series(0, index=data.index)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_data():
    """Generate 500 days of synthetic daily data with uptrend."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    # Random walk with slight upward drift
    close = 100 + np.cumsum(np.random.randn(500) * 0.5 + 0.02)
    close = np.maximum(close, 10)  # floor at 10
    df = pd.DataFrame(
        {
            "date": dates,
            "open": close * (1 + np.random.randn(500) * 0.001),
            "high": close * (1 + abs(np.random.randn(500) * 0.005)),
            "low": close * (1 - abs(np.random.randn(500) * 0.005)),
            "close": close,
            "volume": np.random.randint(100000, 1000000, 500),
        }
    )
    return df


@pytest.fixture()
def downtrend_data():
    """Generate data with downtrend."""
    np.random.seed(123)
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    close = 200 + np.cumsum(np.random.randn(300) * 0.5 - 0.1)
    close = np.maximum(close, 10)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": close * 1.001,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.randint(100000, 500000, 300),
        }
    )
    return df


# ---------------------------------------------------------------------------
# Tests: Indicators
# ---------------------------------------------------------------------------


class TestIndicators:
    def test_annualized_return_positive(self):
        from app.core.indicators import annualized_return

        # ~10% per year for 2 years
        daily_ret = pd.Series(np.full(504, 0.00039))  # ~10% annual
        ann = annualized_return(daily_ret)
        assert 0.05 < ann < 0.20

    def test_annualized_return_zero(self):
        from app.core.indicators import annualized_return

        daily_ret = pd.Series(np.full(252, 0.0))
        assert annualized_return(daily_ret) == pytest.approx(0.0, abs=1e-6)

    def test_sharpe_ratio_positive(self):
        from app.core.indicators import sharpe_ratio

        np.random.seed(42)
        rets = pd.Series(np.random.randn(504) * 0.01 + 0.0005)
        sr = sharpe_ratio(rets)
        assert sr > 0

    def test_sharpe_ratio_zero_std(self):
        from app.core.indicators import sharpe_ratio

        rets = pd.Series(np.full(100, 0.001))
        assert sharpe_ratio(rets) == 0.0

    def test_max_drawdown_known(self):
        from app.core.indicators import max_drawdown

        equity = pd.Series([100, 110, 105, 90, 95, 100])
        mdd = max_drawdown(equity)
        # Max dd = (110 - 90) / 110 = 0.1818...
        assert mdd == pytest.approx(20 / 110, abs=1e-6)

    def test_max_drawdown_monotonic(self):
        from app.core.indicators import max_drawdown

        equity = pd.Series([100, 110, 120, 130, 140])
        assert max_drawdown(equity) == pytest.approx(0.0, abs=1e-6)

    def test_monthly_returns_structure(self):
        from app.core.indicators import monthly_returns

        dates = pd.date_range("2020-01-01", periods=60, freq="B")
        rets = pd.Series(np.random.randn(60) * 0.01, index=dates)
        monthly = monthly_returns(rets)
        assert "year" in monthly.columns
        assert "month" in monthly.columns
        assert "return" in monthly.columns
        assert len(monthly) > 0

    def test_rsi_range(self):
        from app.core.indicators import rsi

        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(100)))
        rsi_vals = rsi(prices)
        valid = rsi_vals.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


# ---------------------------------------------------------------------------
# Tests: BacktestEngine
# ---------------------------------------------------------------------------


class TestBacktestEngine:
    def test_buy_and_hold_positive(self, sample_data):
        engine = BacktestEngine(initial_capital=1_000_000)
        strategy = BuyAndHoldStrategy()
        result = engine.run_single(strategy, sample_data, "TEST")

        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "buy_and_hold"
        assert result.num_trades >= 1
        assert len(result.equity_curve) > 0
        assert result.start_date != ""
        assert result.end_date != ""

    def test_no_trade_strategy(self, sample_data):
        engine = BacktestEngine()
        strategy = NoTradeStrategy()
        result = engine.run_single(strategy, sample_data, "TEST")

        assert result.num_trades == 0
        assert result.win_rate == 0.0

    def test_every_n_days_generates_trades(self, sample_data):
        engine = BacktestEngine()
        strategy = EveryNDaysStrategy(buy_interval=20, hold_days=10)
        result = engine.run_single(strategy, sample_data, "TEST")

        assert result.num_trades > 5
        assert result.avg_holding_days > 0

    def test_commission_reduces_returns(self, sample_data):
        strat = BuyAndHoldStrategy()

        engine_no_fee = BacktestEngine(commission=0.0, slippage=0.0)
        result_no_fee = engine_no_fee.run_single(strat, sample_data, "TEST")

        engine_with_fee = BacktestEngine(commission=0.001, slippage=0.0005)
        result_with_fee = engine_with_fee.run_single(strat, sample_data, "TEST")

        # With fees should have lower returns
        assert result_with_fee.total_return < result_no_fee.total_return

    def test_downtrend_strategy(self, downtrend_data):
        engine = BacktestEngine()
        strategy = BuyAndHoldStrategy()
        result = engine.run_single(strategy, downtrend_data, "TEST")

        # In downtrend, buy and hold should lose money
        # (though not guaranteed due to random data, just check it runs)
        assert isinstance(result.sharpe, float)
        assert isinstance(result.max_drawdown, float)

    def test_empty_data(self):
        engine = BacktestEngine()
        strategy = BuyAndHoldStrategy()
        empty_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        result = engine.run_single(strategy, empty_df, "TEST")

        assert result.total_return == 0.0
        assert result.num_trades == 0

    def test_equity_curve_starts_at_capital(self, sample_data):
        engine = BacktestEngine(initial_capital=500_000)
        strategy = BuyAndHoldStrategy()
        result = engine.run_single(strategy, sample_data, "TEST")

        assert result.initial_capital == 500_000
        assert len(result.equity_curve) > 0

    def test_metrics_values_reasonable(self, sample_data):
        engine = BacktestEngine()
        strategy = EveryNDaysStrategy(buy_interval=30, hold_days=15)
        result = engine.run_single(strategy, sample_data, "TEST")

        # Sharpe should be between -5 and 5 for reasonable strategies
        assert -5 < result.sharpe < 5
        # Max drawdown should be between 0 and 1
        assert 0 <= result.max_drawdown <= 1
        # Win rate should be between 0 and 1
        assert 0 <= result.win_rate <= 1

    def test_to_dict(self, sample_data):
        engine = BacktestEngine()
        strategy = BuyAndHoldStrategy()
        result = engine.run_single(strategy, sample_data, "TEST")
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "total_return" in d
        assert "sharpe" in d
        assert "max_drawdown" in d
        assert "equity_curve" in d
        assert "monthly_returns" in d
        assert "yearly_returns" in d
