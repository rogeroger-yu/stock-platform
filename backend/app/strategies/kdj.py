"""KDJ Strategy — 随机指标策略。

核心逻辑：
- KDJ 金叉（K 上穿 D）+ J 值从超卖区回升 → 买入
- KDJ 死叉（K 下穿 D）+ J 值从超买区回落 → 卖出

来源：George Lane, 1950s (Stochastic Oscillator)
A股常用 KDJ 变体（引入 J 线 = 3K - 2D）
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from app.core.strategy_base import StrategyBase


def _calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series,
              n: int = 9, m1: int = 3, m2: int = 3):
    """计算 KDJ 指标。"""
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()

    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)

    # K = SMA(RSV, m1), D = SMA(K, m2)
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d

    return k, d, j


class KDJStrategy(StrategyBase):
    """经典 KDJ 金叉/死叉策略。

    Parameters:
        n (int): RSV 周期，默认 9
        m1 (int): K 平滑因子，默认 3
        m2 (int): D 平滑因子，默认 3
        oversold (float): 超卖阈值，默认 20
        overbought (float): 超买阈值，默认 80
        min_holding (int): 最短持仓天数，默认 5
        require_j_confirm (bool): 是否要求 J 值确认，默认 True
    """

    DEFAULT_PARAMS = {
        "n": 9,
        "m1": 3,
        "m2": 3,
        "oversold": 20,
        "overbought": 80,
        "min_holding": 5,
        "require_j_confirm": True,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "kdj"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        p = self._params
        k, d, j = _calc_kdj(data["high"], data["low"], data["close"], p["n"], p["m1"], p["m2"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = p["n"] + 5

        for i in range(warmup, len(data)):
            if not in_position:
                # 金叉：K 上穿 D，且 K/D 在超卖区附近
                cross_up = k.iloc[i] > d.iloc[i] and k.iloc[i - 1] <= d.iloc[i - 1]
                in_oversold = k.iloc[i] < 50  # 在中轴以下金叉更有意义

                ok = cross_up and in_oversold
                if p["require_j_confirm"] and ok:
                    ok = j.iloc[i] > j.iloc[i - 1]  # J 值在回升

                if ok:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 死叉：K 下穿 D
                    cross_down = k.iloc[i] < d.iloc[i] and k.iloc[i - 1] >= d.iloc[i - 1]
                    overbought = j.iloc[i] > p["overbought"]

                    if cross_down or overbought:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class KDJReversalStrategy(StrategyBase):
    """KDJ 超卖反转策略：只在 J 值极端超卖后回升时买入。

    更保守，信号更少但准确率更高。
    """

    DEFAULT_PARAMS = {
        "n": 9,
        "m1": 3,
        "m2": 3,
        "j_oversold": -10,  # J 值极端超卖
        "j_overbought": 100,
        "min_holding": 10,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "kdj_reversal"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        p = self._params
        k, d, j = _calc_kdj(data["high"], data["low"], data["close"], p["n"], p["m1"], p["m2"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        for i in range(p["n"] + 5, len(data)):
            if not in_position:
                # J 值从极端超卖回升
                if j.iloc[i - 1] < p["j_oversold"] and j.iloc[i] > p["j_oversold"]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    if j.iloc[i] > p["j_overbought"]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
