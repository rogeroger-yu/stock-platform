"""Strategy Registry — maps strategy type keys to implementation classes.

All built-in and open-source strategies are registered here.
New strategies just need to:
1. Create a class inheriting StrategyBase
2. Add an entry to STRATEGY_REGISTRY
"""

from __future__ import annotations
from typing import Type
from app.core.strategy_base import StrategyBase

# Lazy imports to avoid circular dependencies
_STRATEGY_CLASSES: dict[str, Type[StrategyBase]] = {}


def _load_registry():
    """Populate the registry (called once on first access)."""
    if _STRATEGY_CLASSES:
        return

    from app.strategies.momentum import MomentumStrategy, MomentumBreakoutStrategy
    from app.strategies.mean_reversion import MeanReversionStrategy, PairsMeanReversionStrategy
    from app.strategies.factor_score import FactorScoreStrategy
    from app.strategies.macd import MACDStrategy, MACDHistogramStrategy
    from app.strategies.bollinger_breakout import BollingerBreakoutStrategy, BollingerSqueezeStrategy
    from app.strategies.kdj import KDJStrategy, KDJReversalStrategy
    from app.strategies.turtle import TurtleStrategy, TurtleSystem2Strategy
    from app.strategies.dual_ma import DualMAStrategy, TripleMAStrategy

    registry = {
        # ─── Original 3 families ───
        "momentum": MomentumStrategy,
        "momentum_breakout": MomentumBreakoutStrategy,
        "mean_reversion": MeanReversionStrategy,
        "pairs_mean_reversion": PairsMeanReversionStrategy,
        "factor_score": FactorScoreStrategy,

        # ─── Open-source classics ───
        "macd": MACDStrategy,
        "macd_histogram": MACDHistogramStrategy,
        "bollinger_breakout": BollingerBreakoutStrategy,
        "bollinger_squeeze": BollingerSqueezeStrategy,
        "kdj": KDJStrategy,
        "kdj_reversal": KDJReversalStrategy,
        "turtle": TurtleStrategy,
        "turtle_system2": TurtleSystem2Strategy,
        "dual_ma": DualMAStrategy,
        "triple_ma": TripleMAStrategy,
    }

    _STRATEGY_CLASSES.update(registry)


def get_strategy_class(strategy_type: str) -> Type[StrategyBase] | None:
    """Get strategy class by type key. Returns None if not found."""
    _load_registry()
    return _STRATEGY_CLASSES.get(strategy_type)


def list_strategy_types() -> list[dict]:
    """List all available strategy types with metadata."""
    _load_registry()
    result = []
    for key, cls in _STRATEGY_CLASSES.items():
        # Instantiate with defaults to get param info
        try:
            instance = cls()
            result.append({
                "type": key,
                "name": instance.name,
                "default_params": instance.params,
            })
        except Exception:
            result.append({"type": key, "name": key, "default_params": {}})
    return result
