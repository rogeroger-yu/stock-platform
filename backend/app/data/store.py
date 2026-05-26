"""Local data storage using Parquet files and SQLite."""

import os
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PARQUET_DIR = DATA_DIR / "parquet"
DB_PATH = DATA_DIR / "stock_platform.db"


def ensure_dirs() -> None:
    """确保数据目录存在。"""
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_stock_daily(df: pd.DataFrame, symbol: str) -> str:
    """保存个股日线到 parquet。

    Path: data/parquet/{symbol}.parquet

    Returns:
        The path the file was saved to.
    """
    ensure_dirs()
    path = PARQUET_DIR / f"{symbol}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    return str(path)


def load_stock_daily(symbol: str) -> pd.DataFrame:
    """从 parquet 加载个股日线。"""
    path = PARQUET_DIR / f"{symbol}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No data for {symbol}")
    return pd.read_parquet(path, engine="pyarrow")


def save_metadata(df: pd.DataFrame) -> None:
    """保存股票列表元数据到 sqlite。

    Table name: stock_list
    """
    ensure_dirs()
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("stock_list", conn, if_exists="replace", index=False)


def load_metadata() -> pd.DataFrame:
    """加载股票列表元数据。"""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM stock_list", conn)


def get_data_coverage(symbol: str) -> dict:
    """返回某只股票的数据覆盖范围。

    Returns:
        {
            'start': '2015-01-05',
            'end': '2024-12-31',
            'rows': 2400,
            'missing_pct': 0.5,
        }
    """
    df = load_stock_daily(symbol)

    if df.empty:
        return {"start": None, "end": None, "rows": 0, "missing_pct": 100.0}

    start = df["date"].min()
    end = df["date"].max()
    rows = len(df)

    # Rough estimate: ~240 trading days per year
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    years = (end_dt - start_dt).days / 365.25
    expected_rows = int(years * 240)

    missing_pct = (
        round((1 - rows / expected_rows) * 100, 2) if expected_rows > 0 else 0.0
    )

    return {
        "start": str(start_dt.date()),
        "end": str(end_dt.date()),
        "rows": rows,
        "missing_pct": missing_pct,
    }


def list_available_stocks() -> list[str]:
    """列出所有有数据的股票代码。"""
    ensure_dirs()
    return [f.stem for f in PARQUET_DIR.glob("*.parquet")]
