"""Data fetching layer using akshare."""

import time
import akshare as ak
import pandas as pd
from datetime import datetime

# Column name mapping: akshare Chinese -> English
_COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "amount",
    "换手率": "turnover",
}


def _classify_market(code: str) -> str:
    """Classify stock market by code prefix.

    Args:
        code: 6-digit stock code.

    Returns:
        'sh' for Shanghai, 'sz' for Shenzhen, 'bj' for Beijing.
    """
    if code.startswith("6"):
        return "sh"
    elif code.startswith(("0", "3")):
        return "sz"
    elif code.startswith(("8", "4")):
        return "bj"
    return "unknown"


def fetch_stock_list() -> pd.DataFrame:
    """获取全部 A 股列表。

    Uses ak.stock_zh_a_spot_em() to get the current listed A-share stocks.

    Returns:
        DataFrame with columns: code, name, market (sh/sz/bj)
    """
    df = ak.stock_zh_a_spot_em()
    # The returned DataFrame has '代码' and '名称' columns
    result = pd.DataFrame({
        "code": df["代码"].astype(str).str.zfill(6),
        "name": df["名称"],
    })
    result["market"] = result["code"].apply(_classify_market)
    return result


def fetch_stock_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """获取个股日线数据（前复权）。

    Uses ak.stock_zh_a_hist() with the specified parameters.

    Args:
        symbol: 6-digit stock code, e.g. '000001'.
        start_date: 'YYYYMMDD' format.
        end_date: 'YYYYMMDD' format.
        adjust: 'qfq' forward-adjusted, 'hfq' backward-adjusted, '' unadjusted.

    Returns:
        DataFrame with columns: date(datetime), open, high, low, close,
        volume, amount, turnover.  Sorted by date ascending.
    """
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"Invalid stock code: {symbol!r} (must be 6 digits)")

    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch daily data for {symbol}: {exc}"
        ) from exc

    if df is None or df.empty:
        raise ValueError(
            f"No data returned for {symbol} ({start_date}~{end_date})"
        )

    # Rename Chinese columns to English
    df = df.rename(columns=_COLUMN_MAP)

    # Keep only the columns we need (in case akshare adds extras)
    keep = ["date", "open", "high", "low", "close", "volume", "amount", "turnover"]
    available = [c for c in keep if c in df.columns]
    df = df[available]

    # Convert types
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "turnover"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by date ascending
    df = df.sort_values("date").reset_index(drop=True)

    return df


def fetch_index_daily(
    symbol: str = "000300",
    start_date: str = "20150101",
    end_date: str = "20241231",
) -> pd.DataFrame:
    """获取指数日线数据。

    Uses ak.stock_zh_index_daily_em().  Defaults to CSI 300 (000300).

    Args:
        symbol: Index code, e.g. '000300'.
        start_date: 'YYYYMMDD' format.
        end_date: 'YYYYMMDD' format.

    Returns:
        DataFrame with standardised columns.
    """
    try:
        df = ak.stock_zh_index_daily_em(symbol=symbol)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch index data for {symbol}: {exc}"
        ) from exc

    if df is None or df.empty:
        raise ValueError(f"No data returned for index {symbol}")

    # Standard column names may vary; rename what we can
    rename_map = {
        "日期": "date",
        "date": "date",
        "开盘": "open",
        "open": "open",
        "最高": "high",
        "high": "high",
        "最低": "low",
        "low": "low",
        "收盘": "close",
        "close": "close",
        "成交量": "volume",
        "volume": "volume",
    }
    df = df.rename(columns=rename_map)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        # Filter by date range
        start = pd.to_datetime(start_date, format="%Y%m%d")
        end = pd.to_datetime(end_date, format="%Y%m%d")
        df = df[(df["date"] >= start) & (df["date"] <= end)]

    df = df.sort_values("date").reset_index(drop=True)
    return df
