"""Dual Moving Average Crossover Strategy — 双均线交叉策略。

最经典的均线策略之一：
- 短期均线上穿长期均线 → 买入（金叉）
- 短期均线下穿长期均线 → 卖出（死叉）

来源：经典技术分析，最早由 Granville 提出
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from app.core.strategy_base import StrategyBase
from app.core.indicators import moving_average, exponential_moving_average, rsi as calc_rsi


class DualMAStrategy(StrategyBase):
    """双均线交叉策略。

    Parameters:
        fast_window (int): 短期均线周期，默认 10
        slow_window (int): 长期均线周期，默认 30
        ma_type (str): 均线类型 'sma' 或 'ema'，默认 'ema'
        min_holding (int): 最短持仓天数，默认 10
        use_rsi_filter (bool): RSI 过滤，默认 False
        rsi_upper (float): RSI 超买不买入阈值，默认 70
    """

    DEFAULT_PARAMS = {
        "fast_window": 10,
        "slow_window": 30,
        "ma_type": "ema",
        "min_holding": 10,
        "use_rsi_filter": False,
        "rsi_upper": 70,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "dual_ma"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params
        ma_func = exponential_moving_average if p["ma_type"] == "ema" else moving_average

        fast_ma = ma_func(close, p["fast_window"])
        slow_ma = ma_func(close, p["slow_window"])
        rsi_vals = calc_rsi(close, 14) if p["use_rsi_filter"] else None

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = max(p["fast_window"], p["slow_window"])

        for i in range(warmup + 1, len(data)):
            if not in_position:
                # 金叉
                cross_up = fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i - 1] <= slow_ma.iloc[i - 1]
                ok = True
                if p["use_rsi_filter"] and rsi_vals is not None:
                    if pd.notna(rsi_vals.iloc[i]) and rsi_vals.iloc[i] > p["rsi_upper"]:
                        ok = False
                if cross_up and ok:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 死叉
                    cross_down = fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i - 1] >= slow_ma.iloc[i - 1]
                    if cross_down:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class TripleMAStrategy(StrategyBase):
    """三均线策略：短中长三线确认。

    买入：短 > 中 > 长（多头排列）
    卖出：短 < 中（趋势破坏）
    """

    DEFAULT_PARAMS = {
        "fast_window": 5,
        "mid_window": 20,
        "slow_window": 60,
        "min_holding": 10,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "triple_ma"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params

        fast = exponential_moving_average(close, p["fast_window"])
        mid = exponential_moving_average(close, p["mid_window"])
        slow = exponential_moving_average(close, p["slow_window"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = max(p["fast_window"], p["mid_window"], p["slow_window"])

        for i in range(warmup + 1, len(data)):
            if not in_position:
                # 多头排列：短 > 中 > 长
                if fast.iloc[i] > mid.iloc[i] > slow.iloc[i]:
                    # 前一天不是多头排列（刚形成）
                    if not (fast.iloc[i-1] > mid.iloc[i-1] > slow.iloc[i-1]):
                        signals.iloc[i] = 1
                        in_position = True
                        position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 短线跌破中线
                    if fast.iloc[i] < mid.iloc[i]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
