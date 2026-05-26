"""Walk-Forward Optimization Framework.

IS (In-Sample): 2015-2020 — 用于参数搜索
OOS (Out-of-Sample): 2021-2024 — 用于验证

流程：
1. 在 IS 区间用网格搜索找最优参数
2. 用最优参数在 OOS 区间跑回测
3. 检查 OOS 是否达标（年化≥60%, 回撤≤30%, 夏普≥1.5）
"""

from __future__ import annotations

import itertools
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Type

from app.core.strategy_base import StrategyBase
from app.core.backtest_engine import BacktestEngine, BacktestResult
from app.core.portfolio import PortfolioEngine, PortfolioResult


@dataclass
class WFResult:
    """Walk-forward result for one strategy."""
    strategy_name: str
    best_params: dict
    is_result: dict  # In-sample metrics
    oos_result: dict  # Out-of-sample metrics
    param_grid_size: int
    oos_annualized_return: float = 0.0
    oos_max_drawdown: float = 0.0
    oos_sharpe: float = 0.0
    oos_target_met: bool = False
    all_param_results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "best_params": self.best_params,
            "is_result": self.is_result,
            "oos_result": self.oos_result,
            "param_grid_size": self.param_grid_size,
            "oos_annualized_return": round(self.oos_annualized_return, 4),
            "oos_max_drawdown": round(self.oos_max_drawdown, 4),
            "oos_sharpe": round(self.oos_sharpe, 4),
            "oos_target_met": self.oos_target_met,
        }


@dataclass
class WFBenchmark:
    """OOS 达标基准线。"""
    min_annualized_return: float = 0.60  # ≥60%
    max_drawdown: float = 0.30  # ≤30%
    min_sharpe: float = 1.5  # ≥1.5

    def check(self, ann_ret: float, mdd: float, sharpe: float) -> bool:
        return (
            ann_ret >= self.min_annualized_return
            and mdd <= self.max_drawdown
            and sharpe >= self.min_sharpe
        )


# Default benchmark from user requirements
DEFAULT_BENCHMARK = WFBenchmark(
    min_annualized_return=0.60,
    max_drawdown=0.30,
    min_sharpe=1.5,
)


def walk_forward_single(
    strategy_class: Type[StrategyBase],
    param_grid: dict[str, list],
    data: pd.DataFrame,
    is_start: str = "2015-01-01",
    is_end: str = "2020-12-31",
    oos_start: str = "2021-01-01",
    oos_end: str = "2024-12-31",
    initial_capital: float = 1_000_000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    benchmark: WFBenchmark = DEFAULT_BENCHMARK,
    symbol: str = "unknown",
) -> WFResult:
    """对单个标的跑 walk-forward 优化。

    Args:
        strategy_class: 策略类（不是实例）
        param_grid: 参数网格，如 {"ma_window": [20, 40, 60], "min_holding": [20, 30]}
        data: 完整日期范围的 OHLCV 数据
        is_start/is_end: IS 区间
        oos_start/oos_end: OOS 区间
        benchmark: 达标基准

    Returns:
        WFResult 包含 IS/OOS 结果和最优参数
    """
    # Split data
    df = data.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    df = df.sort_index()

    is_data = df[is_start:is_end].copy()
    oos_data = df[oos_start:oos_end].copy()

    if is_data.empty or oos_data.empty:
        return WFResult(
            strategy_name=strategy_class.__name__,
            best_params={},
            is_result={},
            oos_result={},
            param_grid_size=0,
        )

    # Generate all param combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(itertools.product(*param_values))
    param_grid_size = len(combinations)

    # Grid search on IS
    best_sharpe = -float("inf")
    best_params = {}
    best_is_result = {}
    all_results = []

    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
    )

    for combo in combinations:
        params = dict(zip(param_names, combo))
        try:
            strategy = strategy_class(**params)
            # IS backtest
            is_result = engine.run_single(strategy, is_data, symbol)

            all_results.append({
                "params": params,
                "is_sharpe": is_result.sharpe,
                "is_annualized_return": is_result.annualized_return,
                "is_max_drawdown": is_result.max_drawdown,
            })

            if is_result.sharpe > best_sharpe:
                best_sharpe = is_result.sharpe
                best_params = params
                best_is_result = {
                    "sharpe": is_result.sharpe,
                    "annualized_return": is_result.annualized_return,
                    "max_drawdown": is_result.max_drawdown,
                    "total_return": is_result.total_return,
                    "num_trades": is_result.num_trades,
                }
        except Exception as e:
            all_results.append({"params": params, "error": str(e)})

    # Run OOS with best params
    if not best_params:
        return WFResult(
            strategy_name=strategy_class.__name__,
            best_params={},
            is_result={},
            oos_result={},
            param_grid_size=param_grid_size,
            all_param_results=all_results,
        )

    best_strategy = strategy_class(**best_params)
    oos_result = engine.run_single(best_strategy, oos_data, symbol)

    oos_metrics = {
        "sharpe": oos_result.sharpe,
        "annualized_return": oos_result.annualized_return,
        "max_drawdown": oos_result.max_drawdown,
        "total_return": oos_result.total_return,
        "num_trades": oos_result.num_trades,
        "win_rate": oos_result.win_rate,
    }

    target_met = benchmark.check(
        oos_result.annualized_return,
        oos_result.max_drawdown,
        oos_result.sharpe,
    )

    return WFResult(
        strategy_name=strategy_class.__name__,
        best_params=best_params,
        is_result=best_is_result,
        oos_result=oos_metrics,
        param_grid_size=param_grid_size,
        oos_annualized_return=oos_result.annualized_return,
        oos_max_drawdown=oos_result.max_drawdown,
        oos_sharpe=oos_result.sharpe,
        oos_target_met=target_met,
        all_param_results=all_results,
    )


def walk_forward_portfolio(
    strategy_class: Type[StrategyBase],
    param_grid: dict[str, list],
    data_dict: dict[str, pd.DataFrame],
    is_start: str = "2015-01-01",
    is_end: str = "2020-12-31",
    oos_start: str = "2021-01-01",
    oos_end: str = "2024-12-31",
    initial_capital: float = 1_000_000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    benchmark: WFBenchmark = DEFAULT_BENCHMARK,
) -> WFResult:
    """对多标的组合跑 walk-forward 优化。"""
    # Split data for IS and OOS
    is_data = {}
    oos_data = {}

    for symbol, df in data_dict.items():
        df_copy = df.copy()
        if "date" in df_copy.columns:
            df_copy = df_copy.set_index("date")
        df_copy = df_copy.sort_index()
        is_data[symbol] = df_copy[is_start:is_end].reset_index()
        oos_data[symbol] = df_copy[oos_start:oos_end].reset_index()

    # Grid search
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(itertools.product(*param_values))

    best_sharpe = -float("inf")
    best_params = {}
    best_is_result = {}

    pf_engine = PortfolioEngine(
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
    )

    for combo in combinations:
        params = dict(zip(param_names, combo))
        try:
            strategy = strategy_class(**params)
            is_result = pf_engine.run(strategy, is_data)

            if is_result.sharpe > best_sharpe:
                best_sharpe = is_result.sharpe
                best_params = params
                best_is_result = {
                    "sharpe": is_result.sharpe,
                    "annualized_return": is_result.annualized_return,
                    "max_drawdown": is_result.max_drawdown,
                    "total_return": is_result.total_return,
                    "num_trades": is_result.num_trades,
                }
        except Exception:
            pass

    if not best_params:
        return WFResult(
            strategy_name=strategy_class.__name__,
            best_params={},
            is_result={},
            oos_result={},
            param_grid_size=len(combinations),
        )

    # OOS
    best_strategy = strategy_class(**best_params)
    oos_result = pf_engine.run(best_strategy, oos_data)

    oos_metrics = {
        "sharpe": oos_result.sharpe,
        "annualized_return": oos_result.annualized_return,
        "max_drawdown": oos_result.max_drawdown,
        "total_return": oos_result.total_return,
        "num_trades": oos_result.num_trades,
        "win_rate": oos_result.win_rate,
    }

    target_met = benchmark.check(
        oos_result.annualized_return,
        oos_result.max_drawdown,
        oos_result.sharpe,
    )

    return WFResult(
        strategy_name=strategy_class.__name__,
        best_params=best_params,
        is_result=best_is_result,
        oos_result=oos_metrics,
        param_grid_size=len(combinations),
        oos_annualized_return=oos_result.annualized_return,
        oos_max_drawdown=oos_result.max_drawdown,
        oos_sharpe=oos_result.sharpe,
        oos_target_met=target_met,
    )
