"""Factor Score Strategy — 族 3: 多因子打分选股。

核心逻辑：
- 计算多个因子得分（动量、波动率、成交量、价格形态等）
- 综合打分，高分买入，低分卖出
- 每个因子可独立开关和调权重

持仓约束：≥ 20 交易日
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.core.strategy_base import StrategyBase
from app.core.indicators import (
    moving_average,
    rsi as calc_rsi,
    momentum as calc_momentum,
    exponential_moving_average,
)


class FactorScoreStrategy(StrategyBase):
    """多因子综合打分策略。

    因子列表（默认全部启用）：
    1. momentum_factor: 过去 N 天收益率（动量因子）
    2. volatility_factor: 波动率倒数（低波因子）
    3. volume_factor: 成交量变化率（量价因子）
    4. rsi_factor: RSI 偏离度（超买超卖因子）
    5. trend_factor: 价格与均线的关系（趋势因子）

    买入条件：综合得分 > buy_threshold
    卖出条件：综合得分 < sell_threshold 或持仓超过 min_holding

    Parameters:
        momentum_window (int): 动量窗口，默认 20
        volatility_window (int): 波动率窗口，默认 20
        volume_window (int): 成交量窗口，默认 20
        rsi_period (int): RSI 周期，默认 14
        trend_window (int): 趋势均线窗口，默认 60
        buy_threshold (float): 买入得分阈值，默认 0.6
        sell_threshold (float): 卖出得分阈值，默认 0.3
        min_holding (int): 最短持仓天数，默认 20
        factor_weights (dict): 因子权重，默认等权
    """

    DEFAULT_PARAMS = {
        "momentum_window": 20,
        "volatility_window": 20,
        "volume_window": 20,
        "rsi_period": 14,
        "trend_window": 60,
        "buy_threshold": 0.6,
        "sell_threshold": 0.3,
        "min_holding": 20,
        "factor_weights": {
            "momentum": 0.25,
            "volatility": 0.20,
            "volume": 0.15,
            "rsi": 0.20,
            "trend": 0.20,
        },
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}
        # Merge custom weights if provided
        if "factor_weights" in kwargs:
            self._params["factor_weights"] = {
                **self.DEFAULT_PARAMS["factor_weights"],
                **kwargs["factor_weights"],
            }

    @property
    def name(self) -> str:
        return "factor_score"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def _compute_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有因子得分，归一化到 [0, 1]。"""
        close = data["close"]
        volume = data["volume"] if "volume" in data.columns else pd.Series(0, index=data.index)
        p = self._params

        factors = pd.DataFrame(index=data.index)

        # 1. 动量因子：过去 N 天收益率，归一化到 [0, 1]
        mom = calc_momentum(close, p["momentum_window"])
        factors["momentum"] = self._normalize(mom)

        # 2. 波动率因子：波动率倒数（低波更好）
        vol = close.rolling(window=p["volatility_window"]).std() / close
        factors["volatility"] = self._normalize(-vol)  # 取反，低波=高分

        # 3. 成交量因子：成交量相对变化
        vol_ma = volume.rolling(window=p["volume_window"]).mean()
        vol_ratio = volume / vol_ma
        factors["volume"] = self._normalize(vol_ratio)

        # 4. RSI 因子：RSI 偏离 50 的程度（超卖=高分）
        rsi_vals = calc_rsi(close, p["rsi_period"])
        # RSI < 50 超卖，得分高；RSI > 50 超买，得分低
        factors["rsi"] = self._normalize(100 - rsi_vals)

        # 5. 趋势因子：价格相对均线位置
        trend_ma = moving_average(close, p["trend_window"])
        trend_score = close / trend_ma
        factors["trend"] = self._normalize(trend_score)

        return factors

    def _normalize(self, series: pd.Series) -> pd.Series:
        """归一化到 [0, 1]（min-max）。"""
        s = series.copy()
        s = s.replace([np.inf, -np.inf], np.nan)
        s_min = s.min()
        s_max = s.max()
        if s_max == s_min:
            return pd.Series(0.5, index=series.index)
        return (s - s_min) / (s_max - s_min)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty:
            return pd.Series(0, index=data.index)

        p = self._params
        weights = p["factor_weights"]

        # 计算所有因子
        factors = self._compute_factors(data)

        # 加权综合得分
        composite = pd.Series(0.0, index=data.index)
        for factor_name, weight in weights.items():
            if factor_name in factors.columns:
                composite += factors[factor_name].fillna(0.5) * weight

        # 生成信号
        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        # 需要足够数据计算指标
        warmup = max(
            p["momentum_window"],
            p["volatility_window"],
            p["volume_window"],
            p["rsi_period"],
            p["trend_window"],
        )

        for i in range(warmup, len(data)):
            score = composite.iloc[i]

            if not in_position:
                # 买入：综合得分超过阈值
                if score > p["buy_threshold"]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # 卖出：得分跌破阈值
                    if score < p["sell_threshold"]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals
