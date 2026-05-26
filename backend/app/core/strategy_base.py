from abc import ABC, abstractmethod
import pandas as pd


class StrategyBase(ABC):
    """Abstract base class for all trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""
        ...

    @property
    @abstractmethod
    def params(self) -> dict:
        """Return the strategy parameters."""
        ...

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV columns (open, high, low, close, volume).

        Returns:
            pd.Series of signals: 1 (buy), -1 (sell), 0 (hold).
        """
        ...
