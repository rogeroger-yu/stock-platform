"""Multi-stock portfolio backtesting engine — v1."""

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
)


@dataclass
class PositionState:
    """Current position for one stock."""
    symbol: str
    shares: int = 0
    entry_price: float = 0.0
    entry_date: Optional[pd.Timestamp] = None
    cost: float = 0.0


@dataclass
class PortfolioTrade:
    """A completed trade in the portfolio."""
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
class PortfolioResult:
    """Portfolio-level backtest result."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    calmar: float = 0.0

    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_returns: pd.Series = field(default_factory=pd.Series)

    monthly_ret: pd.DataFrame = field(default_factory=pd.DataFrame)
    yearly_ret: pd.DataFrame = field(default_factory=pd.DataFrame)

    trades: list[PortfolioTrade] = field(default_factory=list)
    num_trades: int = 0
    win_rate: float = 0.0
    avg_holding_days: float = 0.0
    avg_turnover: float = 0.0

    # Per-stock breakdown
    stock_returns: dict = field(default_factory=dict)  # symbol -> total_return

    strategy_name: str = ""
    strategy_params: dict = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 0.0
    commission_rate: float = 0.0
    slippage_rate: float = 0.0
    symbols: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
            "symbols": self.symbols,
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
            "avg_turnover": round(self.avg_turnover, 4),
            "stock_returns": {k: round(v, 4) for k, v in self.stock_returns.items()},
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
            "equity_curve": self.equity_curve.to_dict(orient="records")
            if not self.equity_curve.empty else [],
            "monthly_returns": self.monthly_ret.to_dict(orient="records")
            if not self.monthly_ret.empty else [],
            "yearly_returns": self.yearly_ret.to_dict(orient="records")
            if not self.yearly_ret.empty else [],
        }


class PortfolioEngine:
    """Multi-stock portfolio backtesting engine.

    Supports:
    - Equal-weight or custom-weight allocation
    - Per-stock signal generation
    - Commission and slippage
    - Rebalancing on signal changes
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

    def run(
        self,
        strategy: StrategyBase,
        data_dict: dict[str, pd.DataFrame],
        weight_mode: str = "equal",
    ) -> PortfolioResult:
        """Run portfolio backtest across multiple stocks.

        Args:
            strategy: Strategy instance. generate_signals() is called per stock.
            data_dict: {symbol: OHLCV DataFrame} for each stock.
            weight_mode: 'equal' for equal-weight, 'signal' for signal-weighted.

        Returns:
            PortfolioResult with combined metrics.
        """
        if not data_dict:
            return PortfolioResult(strategy_name=strategy.name)

        # Generate signals for each stock
        all_signals: dict[str, pd.Series] = {}
        for symbol, df in data_dict.items():
            df_copy = df.copy()
            if "date" in df_copy.columns:
                df_copy = df_copy.set_index("date")
            df_copy = df_copy.sort_index()
            all_signals[symbol] = strategy.generate_signals(df_copy)

        # Find common date range
        all_dates = None
        for symbol, df in data_dict.items():
            df_copy = df.copy()
            if "date" in df_copy.columns:
                df_copy = df_copy.set_index("date")
            dates = set(df_copy.index)
            all_dates = dates if all_dates is None else all_dates.intersection(dates)

        if not all_dates:
            return PortfolioResult(strategy_name=strategy.name)

        common_dates = sorted(all_dates)

        # Simulate portfolio
        trades, daily_values = self._simulate_portfolio(
            data_dict, all_signals, common_dates, weight_mode
        )

        # Build equity curve
        equity_series = pd.Series(daily_values, index=common_dates)
        equity_df = pd.DataFrame({
            "equity": equity_series,
            "returns": equity_series.pct_change().fillna(0),
        })

        # Per-stock returns
        stock_returns = {}
        for symbol in data_dict:
            sym_trades = [t for t in trades if t.symbol == symbol]
            stock_returns[symbol] = sum(t.pnl for t in sym_trades) / self.initial_capital

        # Metrics
        daily_returns = equity_df["returns"]
        total_ret = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1 if len(equity_series) > 0 else 0
        ann_ret = annualized_return(daily_returns)
        sr = sharpe_ratio(daily_returns)
        mdd = max_drawdown(equity_series)

        num_trades = len(trades)
        win_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(win_trades) / num_trades if num_trades > 0 else 0.0
        avg_hold = np.mean([t.holding_days for t in trades]) if num_trades > 0 else 0.0

        return PortfolioResult(
            total_return=total_ret,
            annualized_return=ann_ret,
            sharpe=sr,
            max_drawdown=mdd,
            calmar=ann_ret / mdd if mdd > 0 else 0.0,
            equity_curve=equity_df.reset_index().rename(columns={"index": "date"}),
            daily_returns=daily_returns,
            monthly_ret=monthly_returns(daily_returns),
            yearly_ret=yearly_returns(daily_returns),
            trades=trades,
            num_trades=num_trades,
            win_rate=win_rate,
            avg_holding_days=avg_hold,
            avg_turnover=0.0,  # simplified
            stock_returns=stock_returns,
            strategy_name=strategy.name,
            strategy_params=strategy.params,
            start_date=str(common_dates[0].date()) if common_dates else "",
            end_date=str(common_dates[-1].date()) if common_dates else "",
            initial_capital=self.initial_capital,
            commission_rate=self.commission,
            slippage_rate=self.slippage,
            symbols=list(data_dict.keys()),
        )

    def _simulate_portfolio(
        self,
        data_dict: dict[str, pd.DataFrame],
        all_signals: dict[str, pd.Series],
        common_dates: list,
        weight_mode: str,
    ) -> tuple[list[PortfolioTrade], list[float]]:
        """Simulate portfolio trades and track daily values."""
        trades: list[PortfolioTrade] = []
        positions: dict[str, PositionState] = {}
        daily_values: list[float] = []

        n_symbols = len(data_dict)
        per_stock_capital = self.initial_capital / n_symbols if n_symbols > 0 else 0

        for date in common_dates:
            # Process signals for each stock
            for symbol, df in data_dict.items():
                df_copy = df.copy()
                if "date" in df_copy.columns:
                    df_copy = df_copy.set_index("date")
                df_copy = df_copy.sort_index()

                if date not in df_copy.index:
                    continue

                close = df_copy.loc[date, "close"]
                signals = all_signals[symbol]

                # Get signal index for this date
                if date not in signals.index:
                    continue
                signal = signals.loc[date]

                # Buy
                if signal == 1 and symbol not in positions:
                    buy_price = close * (1 + self.slippage)
                    shares = int(per_stock_capital / buy_price)
                    if shares > 0:
                        cost = shares * buy_price * (1 + self.commission)
                        positions[symbol] = PositionState(
                            symbol=symbol,
                            shares=shares,
                            entry_price=buy_price,
                            entry_date=date,
                            cost=cost,
                        )

                # Sell
                elif signal == -1 and symbol in positions:
                    pos = positions[symbol]
                    sell_price = close * (1 - self.slippage)
                    revenue = pos.shares * sell_price * (1 - self.commission)
                    pnl = revenue - pos.cost
                    return_pct = pnl / pos.cost
                    holding_days = (date - pos.entry_date).days

                    trades.append(PortfolioTrade(
                        symbol=symbol,
                        entry_date=pos.entry_date,
                        exit_date=date,
                        entry_price=pos.entry_price,
                        exit_price=sell_price,
                        shares=pos.shares,
                        pnl=pnl,
                        return_pct=return_pct,
                        holding_days=holding_days,
                    ))
                    del positions[symbol]

            # Calculate portfolio value for this date
            portfolio_value = 0
            cash_remaining = self.initial_capital

            for symbol, pos in positions.items():
                df_copy = data_dict[symbol].copy()
                if "date" in df_copy.columns:
                    df_copy = df_copy.set_index("date")
                df_copy = df_copy.sort_index()

                if date in df_copy.index:
                    current_price = df_copy.loc[date, "close"]
                    stock_value = pos.shares * current_price
                    portfolio_value += stock_value
                    cash_remaining -= pos.cost
                else:
                    portfolio_value += pos.cost

            # Add uninvested cash
            invested = sum(p.cost for p in positions.values())
            cash = self.initial_capital - invested
            daily_values.append(portfolio_value + cash)

        # Close all open positions at end
        if positions:
            last_date = common_dates[-1]
            for symbol, pos in list(positions.items()):
                df_copy = data_dict[symbol].copy()
                if "date" in df_copy.columns:
                    df_copy = df_copy.set_index("date")
                if last_date in df_copy.index:
                    sell_price = df_copy.loc[last_date, "close"] * (1 - self.slippage)
                    revenue = pos.shares * sell_price * (1 - self.commission)
                    pnl = revenue - pos.cost
                    trades.append(PortfolioTrade(
                        symbol=symbol,
                        entry_date=pos.entry_date,
                        exit_date=last_date,
                        entry_price=pos.entry_price,
                        exit_price=sell_price,
                        shares=pos.shares,
                        pnl=pnl,
                        return_pct=pnl / pos.cost,
                        holding_days=(last_date - pos.entry_date).days,
                    ))

        return trades, daily_values
