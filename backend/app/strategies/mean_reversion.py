"""Mean Reversion Strategy — 族 2: 均值回归。

核心逻辑：
- 价格偏离均线超过 N 个标准差 → 反向交易
- 布林带突破 + RSI 极值确认
- 价格回归均线时平仓

持仓约束：≥ 20 交易日
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.core.strategy_base import StrategyBase
from app.core.indicators import (
    moving_average,
    rsi as calc_rsi,
    bollinger_bands,
    exponential_moving_average,
)


class MeanReversionStrategy(StrategyBase):
    """基于布林带 + RSI 的均值回归策略。

    买入条件（全部满足）：
    1. 价格跌破布林带下轨
    2. RSI < rsi_lower（超卖）
    3. 价格在长期均线之上（趋势过滤，避免接飞刀）

    卖出条件（任一满足）：
    1. 价格突破布林带上轨
    2. RSI > rsi_upper（超买）
    3. 持仓超过 min_holding 且回到均线附近

    Parameters:
        bb_window (int): 布林带窗口，默认 20
        bb_std (float): 布林带标准差倍数，默认 2.0
        rsi_period (int): RSI 周期，默认 14
        rsi_lower (float): RSI 超卖阈值，默认 30
        rsi_upper (float): RSI 超买阈值，默认 70
        trend_window (int): 趋势过滤均线窗口，默认 120
        min_holding (int): 最短持仓天数，默认 20
        mean_revert_target (float): 回归目标（几分位），默认 0.5（中轨）
    """

    DEFAULT_PARAMS = {
        "bb_window": 20,
        "bb_std": 2.0,
        "rsi_period": 14,
        "rsi_lower": 30,
        "rsi_upper": 70,
        "trend_window": 120,
        "min_holding": 20,
        "mean_revert_target": 0.5,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "mean_reversion"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty or len(data) < self._params["trend_window"]:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params

        # 计算指标
        upper, middle, lower = bollinger_bands(close, p["bb_window"], p["bb_std"])
        rsi_vals = calc_rsi(close, p["rsi_period"])
        trend_ma = moving_average(close, p["trend_window"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        start_idx = max(p["bb_window"], p["rsi_period"], p["trend_window"])

        for i in range(start_idx, len(data)):
            price = close.iloc[i]

            if not in_position:
                # 买入条件：
                # 1. 价格跌破布林带下轨（超卖）
                # 2. RSI 超卖
                # 3. 价格在长期均线之上（大趋势向上）
                below_lower = price < lower.iloc[i]
                rsi_oversold = pd.notna(rsi_vals.iloc[i]) and rsi_vals.iloc[i] < p["rsi_lower"]
                above_trend = price > trend_ma.iloc[i]

                if below_lower and rsi_oversold and above_trend:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0

            else:
                position_held += 1

                if position_held >= p["min_holding"]:
                    # 卖出条件：
                    # 1. 价格突破布林带上轨（超买）
                    # 2. RSI 超买
                    # 3. 回到均线附近（均值回归完成）
                    above_upper = price > upper.iloc[i]
                    rsi_overbought = pd.notna(rsi_vals.iloc[i]) and rsi_vals.iloc[i] > p["rsi_upper"]
                    near_middle = abs(price - middle.iloc[i]) / middle.iloc[i] < 0.02

                    if above_upper or rsi_overbought or near_middle:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class PairsMeanReversionStrategy(StrategyBase):
    """配对交易均值回归（简化版）：基于价差的均值回归。

    适用于单标的场景：用价格与其自身移动均线的偏离度作为信号。
    """

    DEFAULT_PARAMS = {
        "lookback": 60,
        "z_entry": 2.0,
        "z_exit": 0.5,
        "min_holding": 20,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "pairs_mean_reversion"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty or len(data) < self._params["lookback"]:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params

        # Z-score of price relative to its moving average
        ma = moving_average(close, p["lookback"])
        std = close.rolling(window=p["lookback"]).std()
        z_score = (close - ma) / std

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0
        entry_z = 0

        for i in range(p["lookback"], len(data)):
            z = z_score.iloc[i]

            if not in_position:
                # 买入：Z-score 极度负（价格远低于均线）
                if pd.notna(z) and z < -p["z_entry"]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
                    entry_z = z
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 卖出：Z-score 回归到接近 0
                    if pd.notna(z) and z > -p["z_exit"]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
