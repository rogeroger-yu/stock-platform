"""Backtesting engine — v0: single stock, fixed holding period, full metrics."""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from app.core.strategy_base import StrategyBase
from app.core.indicators import (
    annualized_return,
    sharpe_ratio,
    max_drawdown,
    monthly_returns,
    yearly_returns,
    turnover_rate,
)


@dataclass
class TradeRecord:
    """A single completed trade."""
    symbol: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    return_pct: float
    holding_days: int


@dataclass
class BacktestResult:
    """Complete backtest output."""
    # Summary metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    calmar: float = 0.0

    # Time series
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_returns: pd.Series = field(default_factory=pd.Series)

    # Breakdown
    monthly_ret: pd.DataFrame = field(default_factory=pd.DataFrame)
    yearly_ret: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Trade details
    trades: list[TradeRecord] = field(default_factory=list)
    num_trades: int = 0
    win_rate: float = 0.0
    avg_holding_days: float = 0.0
    turnover: float = 0.0

    # Metadata
    strategy_name: str = ""
    strategy_params: dict = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 0.0
    commission_rate: float = 0.0
    slippage_rate: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_return": round(self.total_return, 4),
            "annualized_return": round(self.annualized_return, 4),
            "sharpe": round(self.sharpe, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "calmar": round(self.calmar, 4),
            "num_trades": self.num_trades,
            "win_rate": round(self.win_rate, 4),
            "avg_holding_days": round(self.avg_holding_days, 1),
            "turnover": round(self.turnover, 4),
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
            "equity_curve": self.equity_curve.to_dict(orient="records")
            if not self.equity_curve.empty
            else [],
            "monthly_returns": self.monthly_ret.to_dict(orient="records")
            if not self.monthly_ret.empty
            else [],
            "yearly_returns": self.yearly_ret.to_dict(orient="records")
            if not self.yearly_ret.empty
            else [],
        }


class BacktestEngine:
    """Engine for running strategy backtests against historical data.

    Supports:
    - Single or multi-stock portfolios
    - Commission and slippage
    - Pluggable strategies via StrategyBase
    - Full metrics output
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run_single(
        self,
        strategy: StrategyBase,
        data: pd.DataFrame,
        symbol: str = "unknown",
    ) -> BacktestResult:
        """Run backtest on a single stock.

        Args:
            strategy: Strategy instance that generates signals.
            data: OHLCV DataFrame with datetime index.
                  Must have columns: date, open, high, low, close, volume.
            symbol: Stock code for labeling.

        Returns:
            BacktestResult with all metrics.
        """
        if data.empty:
            return BacktestResult(strategy_name=strategy.name)

        # Ensure date is index
        df = data.copy()
        if "date" in df.columns:
            df = df.set_index("date")
        df = df.sort_index()

        # Generate signals: 1=buy, -1=sell, 0=hold
        signals = strategy.generate_signals(df)

        # Simulate trades
        trades = self._simulate_trades_single(df, signals, symbol)

        # Build equity curve
        equity_curve = self._build_equity_curve(df, trades, symbol)

        # Calculate metrics
        result = self._calculate_metrics(
            equity_curve=equity_curve,
            trades=trades,
            strategy_name=strategy.name,
            strategy_params=strategy.params,
            start_date=str(df.index[0].date()) if len(df) > 0 else "",
            end_date=str(df.index[-1].date()) if len(df) > 0 else "",
        )

        return result

    def _simulate_trades_single(
        self, df: pd.DataFrame, signals: pd.Series, symbol: str
    ) -> list[TradeRecord]:
        """Simulate trades for a single stock based on signals.

        Position sizing: full capital per trade (all-in/all-out).
        """
        trades: list[TradeRecord] = []
        position: Optional[dict] = None  # {entry_date, entry_price, shares}

        for i in range(len(df)):
            date = df.index[i]
            close = df["close"].iloc[i]
            signal = signals.iloc[i] if i < len(signals) else 0

            # Buy signal and no position
            if signal == 1 and position is None:
                # Apply slippage: buy at slightly higher price
                buy_price = close * (1 + self.slippage)
                # Commission on buy
                available = self.initial_capital * (1 - self.commission)
                shares = int(available / buy_price)
                if shares > 0:
                    cost = shares * buy_price * (1 + self.commission)
                    position = {
                        "entry_date": date,
                        "entry_price": buy_price,
                        "shares": shares,
                        "cost": cost,
                    }

            # Sell signal and has position
            elif signal == -1 and position is not None:
                # Apply slippage: sell at slightly lower price
                sell_price = close * (1 - self.slippage)
                revenue = position["shares"] * sell_price * (1 - self.commission)
                pnl = revenue - position["cost"]
                return_pct = pnl / position["cost"]
                holding_days = (date - position["entry_date"]).days

                trades.append(
                    TradeRecord(
                        symbol=symbol,
                        entry_date=position["entry_date"],
                        exit_date=date,
                        entry_price=position["entry_price"],
                        exit_price=sell_price,
                        shares=position["shares"],
                        pnl=pnl,
                        return_pct=return_pct,
                        holding_days=holding_days,
                    )
                )
                position = None

        # If still holding at end, close position
        if position is not None:
            last_close = df["close"].iloc[-1]
            sell_price = last_close * (1 - self.slippage)
            revenue = position["shares"] * sell_price * (1 - self.commission)
            pnl = revenue - position["cost"]
            return_pct = pnl / position["cost"]
            holding_days = (df.index[-1] - position["entry_date"]).days

            trades.append(
                TradeRecord(
                    symbol=symbol,
                    entry_date=position["entry_date"],
                    exit_date=df.index[-1],
                    entry_price=position["entry_price"],
                    exit_price=sell_price,
                    shares=position["shares"],
                    pnl=pnl,
                    return_pct=return_pct,
                    holding_days=holding_days,
                )
            )

        return trades

    def _build_equity_curve(
        self, df: pd.DataFrame, trades: list[TradeRecord], symbol: str
    ) -> pd.DataFrame:
        """Build daily equity curve from trades."""
        equity = pd.Series(dtype=float)
        cash = self.initial_capital
        position_shares = 0
        position_entry_idx = None

        # Build a mapping of trade entry/exit dates
        trade_map: dict = {}
        for t in trades:
            trade_map[t.entry_date] = {"action": "buy", "trade": t}
            trade_map[t.exit_date] = {"action": "sell", "trade": t}

        for i in range(len(df)):
            date = df.index[i]
            close = df["close"].iloc[i]

            if date in trade_map:
                info = trade_map[date]
                if info["action"] == "buy":
                    t = info["trade"]
                    position_shares = t.shares
                    cash = 0  # All-in
                elif info["action"] == "sell":
                    t = info["trade"]
                    cash = t.shares * t.exit_price * (1 - self.commission)
                    position_shares = 0

            # Portfolio value
            portfolio_value = cash + position_shares * close
            equity[date] = portfolio_value

        result = pd.DataFrame(
            {"equity": equity, "returns": equity.pct_change().fillna(0)}
        )
        return result

    def _calculate_metrics(
        self,
        equity_curve: pd.DataFrame,
        trades: list[TradeRecord],
        strategy_name: str,
        strategy_params: dict,
        start_date: str,
        end_date: str,
    ) -> BacktestResult:
        """Calculate all performance metrics."""
        if equity_curve.empty:
            return BacktestResult(strategy_name=strategy_name)

        equity_series = equity_curve["equity"]
        daily_returns = equity_curve["returns"]

        # Core metrics
        total_ret = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1
        ann_ret = annualized_return(daily_returns)
        sr = sharpe_ratio(daily_returns)
        mdd = max_drawdown(equity_series)

        # Monthly/yearly breakdowns
        monthly = monthly_returns(daily_returns)
        yearly = yearly_returns(daily_returns)

        # Trade stats
        num_trades = len(trades)
        win_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(win_trades) / num_trades if num_trades > 0 else 0.0
        avg_hold = (
            np.mean([t.holding_days for t in trades]) if num_trades > 0 else 0.0
        )

        return BacktestResult(
            total_return=total_ret,
            annualized_return=ann_ret,
            sharpe=sr,
            max_drawdown=mdd,
            calmar=ann_ret / mdd if mdd > 0 else 0.0,
            equity_curve=equity_curve.reset_index().rename(
                columns={"index": "date"}
            ),
            daily_returns=daily_returns,
            monthly_ret=monthly,
            yearly_ret=yearly,
            trades=trades,
            num_trades=num_trades,
            win_rate=win_rate,
            avg_holding_days=avg_hold,
            turnover=(
                sum(abs(t.return_pct) for t in trades) / len(trades) * 252 / max(1, len(set(t.symbol for t in trades)))
            )
            if trades
            else 0.0,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            commission_rate=self.commission,
            slippage_rate=self.slippage,
        )
