"""Backtest-to-Trade Bridge — connects backtest signals to paper trade engine.

Flow:
1. User runs a backtest → gets signals
2. Bridge converts signals to actionable orders
3. Paper trade engine executes orders
4. User can monitor live P&L vs backtest expectations

Safety: Only paper/simulated trading. No real money.
"""

from __future__ import annotations

import json
from datetime import datetime, date
from typing import Optional

import pandas as pd

from ..core.backtest_engine import BacktestEngine
from ..core.strategy_base import StrategyBase
from ..paper_trade.engine import PaperTradeEngine, OrderSide, signals_to_orders
from ..strategies import get_strategy_class
from ..data.store import load_stock_daily


class BacktestTradeBridge:
    """Bridges backtest results to paper trading.

    Usage:
        bridge = BacktestTradeBridge(paper_engine)
        bridge.activate_strategy("momentum", {"ma_window": 20}, ["000001"])
        bridge.run_daily_check(date.today())
    """

    def __init__(self, paper_engine: PaperTradeEngine):
        self.paper_engine = paper_engine
        self.active_strategies: list[dict] = []
        self.signal_history: list[dict] = []

    def activate_strategy(
        self,
        strategy_type: str,
        params: dict,
        symbols: list[str],
    ) -> dict:
        """Activate a strategy for live signal monitoring.

        Returns activation confirmation.
        """
        strategy_class = get_strategy_class(strategy_type)
        if not strategy_class:
            return {"error": f"Unknown strategy type: {strategy_type}"}

        strategy = strategy_class(**params)

        activation = {
            "strategy_type": strategy_type,
            "strategy_name": strategy.name,
            "params": params,
            "symbols": symbols,
            "activated_at": datetime.now().isoformat(),
            "status": "active",
        }
        self.active_strategies.append(activation)

        return {
            "status": "activated",
            "strategy": strategy.name,
            "symbols": symbols,
            "message": f"Strategy '{strategy.name}' activated for {len(symbols)} symbols",
        }

    def deactivate_strategy(self, strategy_type: str) -> dict:
        """Deactivate a strategy."""
        before = len(self.active_strategies)
        self.active_strategies = [
            s for s in self.active_strategies if s["strategy_type"] != strategy_type
        ]
        removed = before - len(self.active_strategies)
        return {"status": "deactivated", "removed": removed}

    def get_active_strategies(self) -> list[dict]:
        """List active strategies."""
        return self.active_strategies.copy()

    def run_daily_check(self, as_of_date: Optional[str] = None) -> dict:
        """Check all active strategies for new signals.

        This is the main loop that would run daily in production.
        For now, it runs on-demand.

        Returns:
            {
                "checked": N,
                "signals_found": N,
                "orders_suggested": [...],
                "account_status": {...}
            }
        """
        if not self.active_strategies:
            return {"checked": 0, "signals_found": 0, "orders_suggested": []}

        all_signals: dict[str, int] = {}
        all_prices: dict[str, float] = {}
        signals_detail = []

        for activation in self.active_strategies:
            strategy_class = get_strategy_class(activation["strategy_type"])
            if not strategy_class:
                continue

            strategy = strategy_class(**activation["params"])

            for symbol in activation["symbols"]:
                try:
                    df = load_stock_daily(symbol)
                except FileNotFoundError:
                    continue

                if df.empty:
                    continue

                # Use last N days for signal generation
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()

                # Get signal for latest data
                signals = strategy.generate_signals(df)
                if len(signals) == 0:
                    continue

                latest_signal = signals.iloc[-1]
                latest_price = df["close"].iloc[-1]
                latest_date = df.index[-1]

                if latest_signal != 0:
                    all_signals[symbol] = int(latest_signal)
                    all_prices[symbol] = float(latest_price)
                    signals_detail.append({
                        "symbol": symbol,
                        "signal": int(latest_signal),
                        "signal_label": "BUY" if latest_signal == 1 else "SELL",
                        "price": float(latest_price),
                        "date": str(latest_date.date()),
                        "strategy": activation["strategy_name"],
                    })

                # Also record historical signal
                self.signal_history.append({
                    "symbol": symbol,
                    "strategy": activation["strategy_name"],
                    "signal": int(latest_signal),
                    "price": float(latest_price),
                    "date": str(latest_date.date()),
                    "checked_at": datetime.now().isoformat(),
                })

        # Convert signals to order suggestions
        account = self.paper_engine.get_account()
        order_suggestions = signals_to_orders(all_signals, all_prices, account)

        return {
            "checked": len(self.active_strategies),
            "signals_found": len(signals_detail),
            "signals": signals_detail,
            "orders_suggested": order_suggestions,
            "account_cash": account.cash,
            "account_total_value": account.total_value,
        }

    def execute_suggested_orders(self, suggestions: list[dict]) -> list[dict]:
        """Execute order suggestions through paper trade engine.

        Args:
            suggestions: List from signals_to_orders()

        Returns:
            List of execution results
        """
        results = []
        for order in suggestions:
            result = self.paper_engine.place_order(
                symbol=order["symbol"],
                side=OrderSide(order["side"]),
                quantity=order["quantity"],
                price=order["price"],
            )
            results.append({
                "order_id": result.order_id,
                "symbol": result.symbol,
                "side": result.side.value,
                "quantity": result.filled_quantity,
                "filled_price": result.filled_price,
                "commission": result.commission,
                "status": result.status.value,
            })
        return results

    def get_signal_history(self, limit: int = 100) -> list[dict]:
        """Get recent signal history."""
        return self.signal_history[-limit:]

    def backtest_vs_live(self, strategy_type: str, params: dict, symbols: list[str]) -> dict:
        """Compare backtest performance vs live paper trading.

        Returns metrics from both for comparison.
        """
        strategy_class = get_strategy_class(strategy_type)
        if not strategy_class:
            return {"error": f"Unknown type: {strategy_type}"}

        strategy = strategy_class(**params)
        engine = BacktestEngine()

        backtest_results = {}
        for symbol in symbols:
            try:
                df = load_stock_daily(symbol)
                df["date"] = pd.to_datetime(df["date"])
                result = engine.run_single(strategy, df, symbol)
                backtest_results[symbol] = result.to_dict()
            except Exception as e:
                backtest_results[symbol] = {"error": str(e)}

        # Paper trade stats
        account = self.paper_engine.get_account()
        paper_trades = self.paper_engine.get_trade_log()

        return {
            "backtest_metrics": backtest_results,
            "paper_account": {
                "cash": account.cash,
                "total_value": account.total_value,
                "total_pnl": account.total_pnl,
                "positions": {
                    sym: {
                        "quantity": pos.quantity,
                        "avg_cost": pos.avg_cost,
                        "unrealized_pnl": pos.unrealized_pnl,
                    }
                    for sym, pos in account.positions.items()
                },
            },
            "paper_trades_count": len(paper_trades),
            "paper_trades": paper_trades[-20:],
        }
