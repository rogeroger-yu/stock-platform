"""Turtle Trading Strategy — 海龟交易策略。

核心逻辑：
- 价格突破 20 日最高价 → 买入（系统1入场）
- 价格跌破 10 日最低价 → 卖出（系统1退出）
- ATR 止损 + 金字塔加仓（简化版不加仓）

来源：Richard Dennis & William Eckhardt, 1983
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from app.core.strategy_base import StrategyBase


def _calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


class TurtleStrategy(StrategyBase):
    """海龟交易策略（简化版）。

    入场：价格突破 N 日最高价
    出场：价格跌破 M 日最低价
    止损：入场价 - 2 * ATR

    Parameters:
        entry_window (int): 入场突破窗口，默认 20
        exit_window (int): 出场窗口，默认 10
        atr_period (int): ATR 周期，默认 20
        atr_stop_multiplier (float): ATR 止损倍数，默认 2.0
        min_holding (int): 最短持仓天数，默认 10
    """

    DEFAULT_PARAMS = {
        "entry_window": 20,
        "exit_window": 10,
        "atr_period": 20,
        "atr_stop_multiplier": 2.0,
        "min_holding": 10,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "turtle"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        high = data["high"]
        low = data["low"]
        p = self._params

        # 唐奇安通道
        upper_channel = high.rolling(window=p["entry_window"]).max()
        lower_channel = low.rolling(window=p["exit_window"]).min()
        atr = _calc_atr(high, low, close, p["atr_period"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0
        entry_price = 0.0

        warmup = max(p["entry_window"], p["exit_window"], p["atr_period"])

        for i in range(warmup + 1, len(data)):
            price = close.iloc[i]

            if not in_position:
                # 突破 N 日高点
                if price > upper_channel.iloc[i - 1]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
                    entry_price = price
            else:
                position_held += 1

                # 卖出条件
                sell = False
                if position_held >= p["min_holding"]:
                    # 跌破 M 日低点
                    if price < lower_channel.iloc[i - 1]:
                        sell = True
                    # ATR 止损
                    if pd.notna(atr.iloc[i]):
                        stop_price = entry_price - p["atr_stop_multiplier"] * atr.iloc[i]
                        if price < stop_price:
                            sell = True

                if sell:
                    signals.iloc[i] = -1
                    in_position = False
                    position_held = 0

        return signals


class TurtleSystem2Strategy(StrategyBase):
    """海龟系统2：55日突破入场，20日突破退出。

    更长周期，捕捉大趋势。
    """

    DEFAULT_PARAMS = {
        "entry_window": 55,
        "exit_window": 20,
        "min_holding": 20,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "turtle_system2"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        high = data["high"]
        low = data["low"]
        p = self._params

        upper_channel = high.rolling(window=p["entry_window"]).max()
        lower_channel = low.rolling(window=p["exit_window"]).min()

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = max(p["entry_window"], p["exit_window"])

        for i in range(warmup + 1, len(data)):
            price = close.iloc[i]

            if not in_position:
                if price > upper_channel.iloc[i - 1]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    if price < lower_channel.iloc[i - 1]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
