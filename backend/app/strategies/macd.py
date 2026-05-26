"""MACD Strategy — 经典趋势跟踪策略族。

核心逻辑：
- MACD 金叉（DIF 上穿 DEA）→ 买入
- MACD 死叉（DIF 下穿 DEA）→ 卖出
- 可选：MACD 柱状图过滤 + 零轴过滤

来源：Gerald Appel, 1979
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from app.core.strategy_base import StrategyBase
from app.core.indicators import exponential_moving_average


def _calc_macd(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = exponential_moving_average(close, fast)
    ema_slow = exponential_moving_average(close, slow)
    dif = ema_fast - ema_slow
    dea = exponential_moving_average(dif, signal)
    histogram = 2 * (dif - dea)  # MACD 柱（A股习惯 ×2）
    return dif, dea, histogram


class MACDStrategy(StrategyBase):
    """经典 MACD 金叉/死叉策略。

    Parameters:
        fast_period (int): 快线 EMA 周期，默认 12
        slow_period (int): 慢线 EMA 周期，默认 26
        signal_period (int): 信号线 EMA 周期，默认 9
        min_holding (int): 最短持仓天数，默认 10
        use_zero_filter (bool): 是否要求 DIF 在零轴之上才买入，默认 False
        histogram_filter (bool): 是否要求柱状图为正才买入，默认 False
    """

    DEFAULT_PARAMS = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "min_holding": 10,
        "use_zero_filter": False,
        "histogram_filter": False,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "macd"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty or len(data) < self._params["slow_period"] + self._params["signal_period"]:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params

        dif, dea, hist = _calc_macd(close, p["fast_period"], p["slow_period"], p["signal_period"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = p["slow_period"] + p["signal_period"]

        for i in range(warmup, len(data)):
            if not in_position:
                # 金叉：DIF 上穿 DEA
                cross_up = dif.iloc[i] > dea.iloc[i] and dif.iloc[i - 1] <= dea.iloc[i - 1]

                if cross_up:
                    ok = True
                    if p["use_zero_filter"] and dif.iloc[i] < 0:
                        ok = False
                    if p["histogram_filter"] and hist.iloc[i] <= 0:
                        ok = False
                    if ok:
                        signals.iloc[i] = 1
                        in_position = True
                        position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 死叉：DIF 下穿 DEA
                    cross_down = dif.iloc[i] < dea.iloc[i] and dif.iloc[i - 1] >= dea.iloc[i - 1]
                    if cross_down:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class MACDHistogramStrategy(StrategyBase):
    """MACD 柱状图策略变体：柱状图由负转正买入，由正转负卖出。

    更敏感，适合短线。
    """

    DEFAULT_PARAMS = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "min_holding": 5,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "macd_histogram"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params
        _, _, hist = _calc_macd(close, p["fast_period"], p["slow_period"], p["signal_period"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0
        warmup = p["slow_period"] + p["signal_period"]

        for i in range(warmup + 1, len(data)):
            if not in_position:
                # 柱状图由负转正
                if hist.iloc[i] > 0 and hist.iloc[i - 1] <= 0:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 柱状图由正转负
                    if hist.iloc[i] < 0 and hist.iloc[i - 1] >= 0:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
