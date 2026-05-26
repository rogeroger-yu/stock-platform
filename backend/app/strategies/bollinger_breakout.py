"""Bollinger Bands Breakout Strategy — 布林带突破策略。

核心逻辑：
- 价格突破布林带上轨 + 放量 → 买入（突破追涨）
- 价格跌破布林带中轨 → 卖出（趋势破坏）

来源：John Bollinger, 1980s
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from app.core.strategy_base import StrategyBase
from app.core.indicators import bollinger_bands, moving_average, rsi as calc_rsi


class BollingerBreakoutStrategy(StrategyBase):
    """布林带突破策略。

    买入条件：
    1. 收盘价突破布林带上轨
    2. 成交量 > 均量 * volume_ratio（放量确认）
    3. 可选：RSI 不在极端超买区

    卖出条件：
    1. 收盘价跌破布林带中轨
    2. 或持仓超过 min_holding 且 RSI 超买

    Parameters:
        bb_window (int): 布林带窗口，默认 20
        bb_std (float): 标准差倍数，默认 2.0
        volume_window (int): 均量窗口，默认 20
        volume_ratio (float): 放量倍数，默认 1.5
        min_holding (int): 最短持仓天数，默认 10
        rsi_period (int): RSI 周期，默认 14
        rsi_exit (float): RSI 超买退出阈值，默认 75
    """

    DEFAULT_PARAMS = {
        "bb_window": 20,
        "bb_std": 2.0,
        "volume_window": 20,
        "volume_ratio": 1.5,
        "min_holding": 10,
        "rsi_period": 14,
        "rsi_exit": 75,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "bollinger_breakout"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        volume = data["volume"] if "volume" in data.columns else pd.Series(0, index=data.index)
        p = self._params

        upper, middle, lower = bollinger_bands(close, p["bb_window"], p["bb_std"])
        vol_ma = moving_average(volume, p["volume_window"])
        rsi_vals = calc_rsi(close, p["rsi_period"])

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = max(p["bb_window"], p["volume_window"], p["rsi_period"])

        for i in range(warmup, len(data)):
            price = close.iloc[i]

            if not in_position:
                # 突破上轨 + 放量
                breakout = price > upper.iloc[i]
                vol_ok = volume.iloc[i] > vol_ma.iloc[i] * p["volume_ratio"] if pd.notna(vol_ma.iloc[i]) else False
                rsi_ok = rsi_vals.iloc[i] < 85 if pd.notna(rsi_vals.iloc[i]) else True

                if breakout and vol_ok and rsi_ok:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 跌破中轨 或 RSI 超买
                    below_mid = price < middle.iloc[i]
                    rsi_high = rsi_vals.iloc[i] > p["rsi_exit"] if pd.notna(rsi_vals.iloc[i]) else False

                    if below_mid or rsi_high:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class BollingerSqueezeStrategy(StrategyBase):
    """布林带收窄策略（Squeeze）：带宽收窄后突破方向交易。

    带宽 = (上轨 - 下轨) / 中轨，收窄到历史低位后等突破方向。
    """

    DEFAULT_PARAMS = {
        "bb_window": 20,
        "bb_std": 2.0,
        "squeeze_window": 120,  # 带宽百分位计算窗口
        "squeeze_threshold": 0.1,  # 带宽 < 历史 10% 分位 = 收窄
        "min_holding": 10,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "bollinger_squeeze"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        p = self._params

        upper, middle, lower = bollinger_bands(close, p["bb_window"], p["bb_std"])
        bandwidth = (upper - lower) / middle

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0
        squeeze_active = False

        warmup = max(p["bb_window"], p["squeeze_window"])

        for i in range(warmup, len(data)):
            price = close.iloc[i]
            bw = bandwidth.iloc[i]

            # 检查是否处于收窄状态
            hist_bw = bandwidth.iloc[max(0, i - p["squeeze_window"]):i]
            if pd.notna(bw) and len(hist_bw) > 10:
                percentile = (hist_bw < bw).mean()
                squeeze_active = percentile < p["squeeze_threshold"]

            if not in_position:
                # 收窄后向上突破
                if squeeze_active and price > upper.iloc[i]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    if price < middle.iloc[i]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
