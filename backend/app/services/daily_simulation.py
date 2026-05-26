"""Daily Market Simulation — 每日大盘模拟。

功能：
1. 下载最新行情数据
2. 运行所有策略在主要标的上的回测
3. 生成每日信号报告
4. 模拟交易执行
"""

from __future__ import annotations
import json
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd

from ..core.backtest_engine import BacktestEngine
from ..strategies import get_strategy_class
from ..data.store import load_stock_daily, list_available_stocks
from ..paper_trade.engine import PaperTradeEngine, OrderSide
from ..paper_trade.bridge import BacktestTradeBridge


# 主要跟踪标的
TRACKED_SYMBOLS = [
    "000001",  # 平安银行
    "600000",  # 浦发银行
    "000858",  # 五粮液
    "600519",  # 贵州茅台
    "002594",  # 比亚迪
]


def run_daily_simulation(
    as_of_date: Optional[str] = None,
    symbols: Optional[list[str]] = None,
    paper_engine: Optional[PaperTradeEngine] = None,
) -> dict:
    """运行每日大盘模拟。

    1. 检查所有策略在跟踪标的上的最新信号
    2. 生成信号报告
    3. 如果有 paper_engine，执行模拟交易

    Returns:
        {
            "date": "2026-05-26",
            "symbols_checked": 5,
            "strategies_checked": 17,
            "signals": [...],
            "top_signals": [...],
            "market_summary": {...},
            "executions": [...]
        }
    """
    symbols = symbols or TRACKED_SYMBOLS
    today = as_of_date or date.today().isoformat()

    # Load all strategies from DB (or use defaults)
    from ..strategies.registry import list_strategy_types
    strategy_types = list_strategy_types()

    all_signals = []
    strategy_count = 0

    for strat_info in strategy_types:
        strategy_type = strat_info["type"]
        cls = get_strategy_class(strategy_type)
        if not cls:
            continue

        # Skip composite for daily sim (needs sub-strategy data)
        if strategy_type in ("composite", "adaptive_composite"):
            continue

        try:
            strategy = cls()
        except Exception:
            continue

        strategy_count += 1

        for symbol in symbols:
            try:
                df = load_stock_daily(symbol)
            except FileNotFoundError:
                continue

            if df.empty or len(df) < 120:
                continue

            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()

            # Use last 250 trading days for signal generation
            recent = df.tail(250).copy()

            try:
                signals = strategy.generate_signals(recent)
            except Exception:
                continue

            if len(signals) == 0:
                continue

            latest_signal = int(signals.iloc[-1])
            latest_price = float(recent["close"].iloc[-1])
            latest_date = str(recent.index[-1].date())

            # Calculate recent performance (last 20 days return)
            if len(recent) >= 20:
                ret_20d = (recent["close"].iloc[-1] / recent["close"].iloc[-20] - 1)
            else:
                ret_20d = 0.0

            if latest_signal != 0:
                all_signals.append({
                    "symbol": symbol,
                    "strategy": strategy.name,
                    "strategy_type": strategy_type,
                    "signal": latest_signal,
                    "signal_label": "BUY" if latest_signal == 1 else "SELL",
                    "price": latest_price,
                    "date": latest_date,
                    "return_20d": round(ret_20d, 4),
                    "params": strategy.params,
                })

    # Sort signals: BUY signals first (by 20d return desc), then SELL
    buy_signals = sorted(
        [s for s in all_signals if s["signal"] == 1],
        key=lambda x: x["return_20d"],
        reverse=True,
    )
    sell_signals = [s for s in all_signals if s["signal"] == -1]

    # Market summary
    market_summary = {}
    for symbol in symbols:
        try:
            df = load_stock_daily(symbol)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            if len(df) >= 5:
                last5 = df.tail(5)
                market_summary[symbol] = {
                    "price": float(last5["close"].iloc[-1]),
                    "change_1d": round(float(last5["close"].pct_change().iloc[-1]) * 100, 2),
                    "change_5d": round(float((last5["close"].iloc[-1] / last5["close"].iloc[0] - 1) * 100), 2),
                }
        except Exception:
            continue

    # Execute paper trades if engine provided
    executions = []
    if paper_engine and buy_signals:
        for sig in buy_signals[:3]:  # Top 3 buy signals
            account = paper_engine.get_account()
            if account.cash > sig["price"] * 100:
                quantity = int(account.cash * 0.15 / sig["price"] / 100) * 100
                if quantity > 0:
                    order = paper_engine.place_order(
                        symbol=sig["symbol"],
                        side=OrderSide.BUY,
                        quantity=quantity,
                        price=sig["price"],
                    )
                    executions.append({
                        "order_id": order.order_id,
                        "symbol": sig["symbol"],
                        "quantity": order.filled_quantity,
                        "price": order.filled_price,
                        "strategy": sig["strategy"],
                        "status": order.status.value,
                    })

    return {
        "date": today,
        "symbols_checked": len(symbols),
        "strategies_checked": strategy_count,
        "total_signals": len(all_signals),
        "buy_signals_count": len(buy_signals),
        "sell_signals_count": len(sell_signals),
        "top_buy_signals": buy_signals[:5],
        "top_sell_signals": sell_signals[:5],
        "market_summary": market_summary,
        "executions": executions,
    }


def format_daily_report(result: dict) -> str:
    """格式化每日报告为可读文本。"""
    lines = [
        f"📊 每日大盘模拟报告 — {result['date']}",
        f"检查 {result['symbols_checked']} 只标的 × {result['strategies_checked']} 个策略",
        f"发现 {result['total_signals']} 个信号（买入 {result['buy_signals_count']} / 卖出 {result['sell_signals_count']}）",
        "",
        "📈 大盘概览：",
    ]

    for sym, info in result.get("market_summary", {}).items():
        arrow = "🔴" if info["change_1d"] < 0 else "🟢"
        lines.append(f"  {sym}: ¥{info['price']:.2f} {arrow}{info['change_1d']:+.2f}% (5日{info['change_5d']:+.2f}%)")

    if result.get("top_buy_signals"):
        lines.extend(["", "🟢 Top 买入信号："])
        for s in result["top_buy_signals"]:
            lines.append(f"  {s['symbol']} | {s['strategy']:20s} | ¥{s['price']:.2f} | 20日{s['return_20d']*100:+.1f}%")

    if result.get("top_sell_signals"):
        lines.extend(["", "🔴 Top 卖出信号："])
        for s in result["top_sell_signals"][:3]:
            lines.append(f"  {s['symbol']} | {s['strategy']:20s} | ¥{s['price']:.2f}")

    if result.get("executions"):
        lines.extend(["", "💹 模拟交易执行："])
        for ex in result["executions"]:
            lines.append(f"  买入 {ex['symbol']} {ex['quantity']}股 @ ¥{ex['price']:.2f} [{ex['status']}]")

    return "\n".join(lines)
