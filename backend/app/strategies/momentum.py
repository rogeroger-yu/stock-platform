"""Momentum Strategy — 族 1: 趋势跟踪 / 动量。

核心逻辑：
- 价格突破 N 日均线 → 买入
- 价格跌破 N 日均线 → 卖出
- 可选：RSI 过滤（避免超买追高）

持仓约束：≥ 20 交易日（通过 minimum_holding 参数控制）
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.core.strategy_base import StrategyBase
from app.core.indicators import moving_average, rsi as calc_rsi, momentum as calc_momentum


class MomentumStrategy(StrategyBase):
    """基于价格动量的趋势跟踪策略。

    Parameters:
        ma_window (int): 均线周期，默认 60（季线）
        rsi_period (int): RSI 计算周期，默认 14
        rsi_upper (float): RSI 超买阈值，超过则不买入，默认 70
        rsi_lower (float): RSI 超卖阈值，低于则不卖出，默认 30
        min_holding (int): 最短持仓天数，默认 20
        momentum_window (int): 动量计算窗口，默认 20
        use_momentum_filter (bool): 是否启用动量过滤，默认 True
        momentum_threshold (float): 动量阈值，大于此值才买入，默认 0
    """

    DEFAULT_PARAMS = {
        "ma_window": 60,
        "rsi_period": 14,
        "rsi_upper": 70,
        "rsi_lower": 30,
        "min_holding": 20,
        "momentum_window": 20,
        "use_momentum_filter": True,
        "momentum_threshold": 0.0,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号。

        Args:
            data: OHLCV DataFrame，index 为 datetime。

        Returns:
            pd.Series: 1=买入, -1=卖出, 0=持有
        """
        if data.empty or len(data) < self._params["ma_window"]:
            return pd.Series(0, index=data.index)

        close = data["close"]
        ma_window = self._params["ma_window"]
        rsi_period = self._params["rsi_period"]
        rsi_upper = self._params["rsi_upper"]
        rsi_lower = self._params["rsi_lower"]
        min_holding = self._params["min_holding"]
        mom_window = self._params["momentum_window"]
        use_mom = self._params["use_momentum_filter"]
        mom_threshold = self._params["momentum_threshold"]

        # 计算指标
        ma = moving_average(close, ma_window)
        rsi_vals = calc_rsi(close, rsi_period)
        momentum_vals = calc_momentum(close, mom_window)

        # 生成原始信号
        signals = pd.Series(0, index=data.index)
        position_held = 0  # 0 = 空仓, >0 = 持仓天数
        in_position = False

        for i in range(ma_window, len(data)):
            if not in_position:
                # 买入条件：价格在均线之上
                buy_ok = close.iloc[i] > ma.iloc[i]

                # RSI 过滤：不在超买区
                if pd.notna(rsi_vals.iloc[i]):
                    buy_ok = buy_ok and rsi_vals.iloc[i] < rsi_upper

                # 动量过滤：动量为正
                if use_mom and pd.notna(momentum_vals.iloc[i]):
                    buy_ok = buy_ok and momentum_vals.iloc[i] > mom_threshold

                if buy_ok:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1

                # 卖出条件：价格跌破均线 + 持仓超过最短天数
                if position_held >= min_holding:
                    sell_ok = close.iloc[i] < ma.iloc[i]

                    # RSI 超卖也可以考虑卖出
                    if pd.notna(rsi_vals.iloc[i]) and rsi_vals.iloc[i] < rsi_lower:
                        sell_ok = True

                    if sell_ok:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class MomentumBreakoutStrategy(StrategyBase):
    """动量突破策略变体：价格突破 N 日高点买入，跌破 N 日低点卖出。

    适合趋势更强的市场环境。
    """

    DEFAULT_PARAMS = {
        "breakout_window": 60,
        "exit_window": 20,
        "min_holding": 20,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}

    @property
    def name(self) -> str:
        return "momentum_breakout"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        close = data["close"]
        high = data["high"]
        low = data["low"]

        bk_window = self._params["breakout_window"]
        exit_window = self._params["exit_window"]
        min_holding = self._params["min_holding"]

        high_n = high.rolling(window=bk_window).max()
        low_n = low.rolling(window=exit_window).min()

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        for i in range(max(bk_window, exit_window), len(data)):
            if not in_position:
                if close.iloc[i] > high_n.iloc[i - 1]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= min_holding and close.iloc[i] < low_n.iloc[i - 1]:
                    signals.iloc[i] = -1
                    in_position = False
                    position_held = 0

        return signals
