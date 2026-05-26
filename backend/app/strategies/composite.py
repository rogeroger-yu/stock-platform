"""Composite Strategy — 综合策略：融合多个子策略的信号。

核心思路：
- 多信号投票：至少 N/M 个子策略同意才交易
- 动态权重：根据近期表现调整策略权重
- 市场状态感知：震荡市偏向均值回归，趋势市偏向趋势跟踪

这是"我们的策略"——持续迭代优化的核心策略。
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Type
from app.core.strategy_base import StrategyBase
from app.core.indicators import moving_average, rsi as calc_rsi


class CompositeStrategy(StrategyBase):
    """多策略投票融合策略。

    融合方式：
    1. 每个子策略独立生成信号
    2. 加权投票：signal = sum(weight_i * signal_i)
    3. 买入：加权信号 > buy_threshold
    4. 卖出：加权信号 < sell_threshold

    Parameters:
        sub_strategy_types (list[str]): 子策略类型列表
        sub_strategy_params (list[dict]): 每个子策略的参数
        weights (list[float]): 每个子策略的权重
        buy_threshold (float): 买入阈值，默认 0.5
        sell_threshold (float): 卖出阈值，默认 -0.3
        min_holding (int): 最短持仓天数，默认 10
        min_agreement (int): 最少同意策略数，默认 2
    """

    DEFAULT_PARAMS = {
        "sub_strategy_types": ["pairs_mean_reversion", "bollinger_breakout", "kdj"],
        "sub_strategy_params": [
            {"lookback": 60, "z_entry": 2.0, "z_exit": 0.5, "min_holding": 10},
            {"bb_window": 20, "bb_std": 2.0, "volume_ratio": 1.5, "min_holding": 10},
            {"n": 9, "oversold": 20, "overbought": 80, "min_holding": 5},
        ],
        "weights": [0.4, 0.3, 0.3],
        "buy_threshold": 0.5,
        "sell_threshold": -0.3,
        "min_holding": 10,
        "min_agreement": 2,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}
        self._sub_strategies = self._build_sub_strategies()

    def _build_sub_strategies(self) -> list[StrategyBase]:
        """Instantiate sub-strategies from params."""
        from app.strategies.registry import get_strategy_class

        types = self._params["sub_strategy_types"]
        params_list = self._params["sub_strategy_params"]
        strategies = []

        for i, stype in enumerate(types):
            cls = get_strategy_class(stype)
            if cls:
                sp = params_list[i] if i < len(params_list) else {}
                strategies.append(cls(**sp))

        return strategies

    @property
    def name(self) -> str:
        return "composite"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty or not self._sub_strategies:
            return pd.Series(0, index=data.index)

        # Generate signals from each sub-strategy
        all_signals = []
        for strat in self._sub_strategies:
            try:
                sig = strat.generate_signals(data)
                all_signals.append(sig)
            except Exception:
                all_signals.append(pd.Series(0, index=data.index))

        weights = self._params["weights"]
        if len(weights) < len(all_signals):
            weights.extend([1.0] * (len(all_signals) - len(weights)))

        # Normalize weights
        total_w = sum(weights[:len(all_signals)])
        norm_weights = [w / total_w for w in weights[:len(all_signals)]]

        # Weighted signal
        composite = pd.Series(0.0, index=data.index)
        for sig, w in zip(all_signals, norm_weights):
            composite += sig * w

        # Agreement count
        agreement = pd.Series(0, index=data.index)
        for i in range(len(data)):
            buy_votes = sum(1 for sig in all_signals if sig.iloc[i] == 1)
            sell_votes = sum(1 for sig in all_signals if sig.iloc[i] == -1)
            agreement.iloc[i] = max(buy_votes, sell_votes)

        # Generate final signals
        p = self._params
        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0

        warmup = 120  # enough for all sub-strategies

        for i in range(warmup, len(data)):
            if not in_position:
                # Buy: weighted signal > threshold AND enough agreement
                if composite.iloc[i] > p["buy_threshold"] and agreement.iloc[i] >= p["min_agreement"]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    # Sell: weighted signal < threshold
                    if composite.iloc[i] < p["sell_threshold"]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals


class AdaptiveCompositeStrategy(StrategyBase):
    """自适应复合策略：根据近期表现动态调整子策略权重。

    每 N 天重新评估各子策略的近期表现，表现好的给更多权重。
    """

    DEFAULT_PARAMS = {
        "sub_strategy_types": ["pairs_mean_reversion", "bollinger_breakout", "kdj"],
        "sub_strategy_params": [
            {"lookback": 60, "z_entry": 2.0, "z_exit": 0.5, "min_holding": 10},
            {"bb_window": 20, "bb_std": 2.0, "volume_ratio": 1.5, "min_holding": 10},
            {"n": 9, "oversold": 20, "overbought": 80, "min_holding": 5},
        ],
        "initial_weights": [0.34, 0.33, 0.33],
        "rebalance_window": 60,  # 每 60 天重新评估权重
        "buy_threshold": 0.5,
        "sell_threshold": -0.3,
        "min_holding": 10,
        "min_agreement": 2,
    }

    def __init__(self, **kwargs):
        self._params = {**self.DEFAULT_PARAMS, **kwargs}
        self._sub_strategies = self._build_sub_strategies()

    def _build_sub_strategies(self) -> list[StrategyBase]:
        from app.strategies.registry import get_strategy_class
        types = self._params["sub_strategy_types"]
        params_list = self._params["sub_strategy_params"]
        strategies = []
        for i, stype in enumerate(types):
            cls = get_strategy_class(stype)
            if cls:
                sp = params_list[i] if i < len(params_list) else {}
                strategies.append(cls(**sp))
        return strategies

    @property
    def name(self) -> str:
        return "adaptive_composite"

    @property
    def params(self) -> dict:
        return self._params.copy()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if data.empty or not self._sub_strategies:
            return pd.Series(0, index=data.index)

        p = self._params
        n_strats = len(self._sub_strategies)

        # Generate all sub-signals
        all_signals = [s.generate_signals(data) for s in self._sub_strategies]

        # Track weights over time
        weights = np.array(p["initial_weights"][:n_strats], dtype=float)
        if len(weights) < n_strats:
            weights = np.ones(n_strats) / n_strats

        signals = pd.Series(0, index=data.index)
        in_position = False
        position_held = 0
        rebalance_window = p["rebalance_window"]

        warmup = 120

        for i in range(warmup, len(data)):
            # Rebalance weights periodically
            if i > warmup and i % rebalance_window == 0:
                weights = self._rebalance_weights(all_signals, i, rebalance_window)

            # Weighted signal
            composite = sum(float(all_signals[j].iloc[i]) * weights[j] for j in range(n_strats))

            # Agreement
            buy_votes = sum(1 for sig in all_signals if sig.iloc[i] == 1)
            sell_votes = sum(1 for sig in all_signals if sig.iloc[i] == -1)
            agreement = max(buy_votes, sell_votes)

            if not in_position:
                if composite > p["buy_threshold"] and agreement >= p["min_agreement"]:
                    signals.iloc[i] = 1
                    in_position = True
                    position_held = 0
            else:
                position_held += 1
                if position_held >= p["min_holding"]:
                    if composite < p["sell_threshold"]:
                        signals.iloc[i] = -1
                        in_position = False
                        position_held = 0

        return signals

    def _rebalance_weights(self, all_signals: list, current_idx: int, window: int) -> np.ndarray:
        """Rebalance weights based on recent signal accuracy."""
        start = max(0, current_idx - window)
        n = len(all_signals)
        scores = np.ones(n)

        for j, sig in enumerate(all_signals):
            # Count profitable signals in the window
            buys = []
            sells = []
            for k in range(start, min(current_idx, len(sig))):
                if sig.iloc[k] == 1:
                    buys.append(k)
                elif sig.iloc[k] == -1:
                    sells.append(k)

            # Simple scoring: count of matched buy-sell pairs
            matched = min(len(buys), len(sells))
            scores[j] = matched + 1  # +1 to avoid zero

        # Normalize
        total = scores.sum()
        return scores / total if total > 0 else np.ones(n) / n
