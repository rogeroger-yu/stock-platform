"""Technical and performance indicator calculations."""

import pandas as pd
import numpy as np


def annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Calculate annualized return from a series of periodic returns.

    Args:
        returns: Series of period returns (e.g. daily returns as decimals).
        periods_per_year: Number of periods in a year (252 for trading days).

    Returns:
        Annualized return as a decimal (e.g. 0.15 for 15%).
    """
    if returns.empty:
        return 0.0
    cumulative = (1 + returns).prod()
    n_periods = len(returns)
    if n_periods == 0:
        return 0.0
    return float(cumulative ** (periods_per_year / n_periods) - 1)


def sharpe_ratio(
    returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252
) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns: Series of period returns.
        risk_free_rate: Annual risk-free rate (default 0).
        periods_per_year: Trading days per year.

    Returns:
        Annualized Sharpe ratio.
    """
    if returns.empty or returns.std() < 1e-10:
        return 0.0
    excess = returns - risk_free_rate / periods_per_year
    return float(np.sqrt(periods_per_year) * excess.mean() / excess.std())


def max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown from an equity curve.

    Args:
        equity_curve: Series of portfolio values over time.

    Returns:
        Maximum drawdown as a positive decimal (e.g. 0.25 for 25% drawdown).
    """
    if equity_curve.empty:
        return 0.0
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return float(abs(drawdown.min()))


def calmar_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Calmar ratio = annualized return / max drawdown."""
    ann_ret = annualized_return(returns, periods_per_year)
    # Build equity curve from returns to compute max dd
    equity = (1 + returns).cumprod()
    mdd = max_drawdown(equity)
    if mdd == 0:
        return 0.0
    return float(ann_ret / mdd)


def monthly_returns(returns: pd.Series) -> pd.DataFrame:
    """Aggregate daily returns into monthly returns.

    Args:
        returns: Series with datetime index of daily returns.

    Returns:
        DataFrame with columns: year, month, return
    """
    if returns.empty:
        return pd.DataFrame(columns=["year", "month", "return"])
    grouped = returns.groupby([returns.index.year, returns.index.month])
    monthly = grouped.apply(lambda x: (1 + x).prod() - 1)
    monthly.index.names = ["year", "month"]
    result = monthly.reset_index()
    result.columns = ["year", "month", "return"]
    return result


def yearly_returns(returns: pd.Series) -> pd.DataFrame:
    """Aggregate daily returns into yearly returns."""
    if returns.empty:
        return pd.DataFrame(columns=["year", "return"])
    yearly = returns.groupby(returns.index.year).apply(lambda x: (1 + x).prod() - 1)
    result = yearly.reset_index()
    result.columns = ["year", "return"]
    return result


def turnover_rate(
    positions: pd.DataFrame, periods_per_year: int = 252
) -> float:
    """Calculate annualized turnover rate.

    Args:
        positions: DataFrame where each row is a day, columns are stock weights.
                   Values are portfolio weights (0-1).

    Returns:
        Annualized turnover rate.
    """
    if positions.empty or len(positions) < 2:
        return 0.0
    daily_turnover = positions.diff().abs().sum(axis=1)
    return float(daily_turnover.mean() * periods_per_year)


# --- Technical indicators (for strategy use) ---


def moving_average(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window).mean()


def exponential_moving_average(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def momentum(series: pd.Series, period: int = 20) -> pd.Series:
    """Price momentum (rate of change)."""
    return series.pct_change(periods=period)


def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands. Returns (upper, middle, lower)."""
    middle = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower
