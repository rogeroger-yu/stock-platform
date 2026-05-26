"""Tests for the data layer (fetcher + store).

All tests use mocks — no real network requests.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

SAMPLE_DAILY_DF = pd.DataFrame({
    "日期": ["2024-01-02", "2024-01-03", "2024-01-04"],
    "开盘": [10.0, 10.5, 10.2],
    "最高": [10.8, 10.9, 10.6],
    "最低": [9.8, 10.1, 10.0],
    "收盘": [10.5, 10.2, 10.4],
    "成交量": [100000, 120000, 110000],
    "成交额": [1050000.0, 1224000.0, 1144000.0],
    "换手率": [1.5, 1.8, 1.6],
})

SAMPLE_SPOT_DF = pd.DataFrame({
    "代码": ["000001", "600000", "002594"],
    "名称": ["平安银行", "浦发银行", "比亚迪"],
})


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Patch DATA_DIR / PARQUET_DIR / DB_PATH to a temp directory."""
    import app.data.store as store_mod

    orig_data = store_mod.DATA_DIR
    orig_parquet = store_mod.PARQUET_DIR
    orig_db = store_mod.DB_PATH

    store_mod.DATA_DIR = tmp_path
    store_mod.PARQUET_DIR = tmp_path / "parquet"
    store_mod.DB_PATH = tmp_path / "stock_platform.db"

    yield tmp_path

    store_mod.DATA_DIR = orig_data
    store_mod.PARQUET_DIR = orig_parquet
    store_mod.DB_PATH = orig_db


# ---------------------------------------------------------------------------
# store tests
# ---------------------------------------------------------------------------


class TestStoreParquet:
    """save_stock_daily / load_stock_daily round-trip."""

    def test_save_and_load(self, tmp_data_dir):
        from app.data.store import save_stock_daily, load_stock_daily

        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 10.5],
            "close": [10.5, 10.2],
        })

        path = save_stock_daily(df, "000001")
        assert Path(path).exists()

        loaded = load_stock_daily("000001")
        assert len(loaded) == 2
        assert list(loaded.columns) == ["date", "open", "close"]
        assert loaded["open"].iloc[0] == pytest.approx(10.0)

    def test_load_nonexistent_raises(self, tmp_data_dir):
        from app.data.store import load_stock_daily

        with pytest.raises(FileNotFoundError):
            load_stock_daily("999999")


class TestStoreSqlite:
    """save_metadata / load_metadata round-trip."""

    def test_save_and_load_metadata(self, tmp_data_dir):
        from app.data.store import save_metadata, load_metadata

        df = pd.DataFrame({
            "code": ["000001", "600000"],
            "name": ["平安银行", "浦发银行"],
            "market": ["sz", "sh"],
        })

        save_metadata(df)
        loaded = load_metadata()

        assert len(loaded) == 2
        assert "code" in loaded.columns
        assert "name" in loaded.columns
        assert list(loaded["code"]) == ["000001", "600000"]


class TestListAvailable:
    """list_available_stocks."""

    def test_lists_saved_stocks(self, tmp_data_dir):
        from app.data.store import save_stock_daily, list_available_stocks

        df = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [10.0]})
        save_stock_daily(df, "000001")
        save_stock_daily(df, "600000")

        available = list_available_stocks()
        assert sorted(available) == ["000001", "600000"]


class TestDataCoverage:
    """get_data_coverage."""

    def test_coverage_calculation(self, tmp_data_dir):
        from app.data.store import save_stock_daily, get_data_coverage

        # ~10 years of data, ~2400 rows
        dates = pd.date_range("2015-01-05", periods=2400, freq="B")
        df = pd.DataFrame({"date": dates, "close": range(2400)})
        save_stock_daily(df, "000001")

        cov = get_data_coverage("000001")
        assert cov["rows"] == 2400
        assert cov["start"] == "2015-01-05"
        assert cov["end"] == dates[-1].date().isoformat()
        # missing_pct should be very low (close to 0)
        assert cov["missing_pct"] < 5.0

    def test_coverage_empty(self, tmp_data_dir):
        from app.data.store import save_stock_daily, get_data_coverage

        df = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "close": pd.Series(dtype="float")})
        save_stock_daily(df, "999999")

        cov = get_data_coverage("999999")
        assert cov["rows"] == 0
        assert cov["missing_pct"] == 100.0


# ---------------------------------------------------------------------------
# fetcher tests (mocked)
# ---------------------------------------------------------------------------


class TestFetcherColumns:
    """Verify column renaming and type conversion."""

    @patch("app.data.fetcher.ak")
    def test_fetch_stock_daily_columns(self, mock_ak):
        from app.data.fetcher import fetch_stock_daily

        mock_ak.stock_zh_a_hist.return_value = SAMPLE_DAILY_DF.copy()

        result = fetch_stock_daily("000001", "20240101", "20240131")

        expected_cols = ["date", "open", "high", "low", "close", "volume", "amount", "turnover"]
        assert list(result.columns) == expected_cols
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert result["date"].is_monotonic_increasing

    @patch("app.data.fetcher.ak")
    def test_fetch_stock_list_columns(self, mock_ak):
        from app.data.fetcher import fetch_stock_list

        mock_ak.stock_zh_a_spot_em.return_value = SAMPLE_SPOT_DF.copy()

        result = fetch_stock_list()

        assert list(result.columns) == ["code", "name", "market"]
        assert result["code"].iloc[0] == "000001"
        assert result["market"].iloc[0] == "sz"
        assert result["market"].iloc[1] == "sh"

    @patch("app.data.fetcher.ak")
    def test_fetch_stock_daily_empty_raises(self, mock_ak):
        from app.data.fetcher import fetch_stock_daily

        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame()

        with pytest.raises(ValueError, match="No data returned"):
            fetch_stock_daily("000001", "20240101", "20240131")

    def test_fetch_stock_daily_invalid_code(self):
        from app.data.fetcher import fetch_stock_daily

        with pytest.raises(ValueError, match="Invalid stock code"):
            fetch_stock_daily("abc", "20240101", "20240131")

    @patch("app.data.fetcher.ak")
    def test_fetch_stock_daily_sorts_ascending(self, mock_ak):
        from app.data.fetcher import fetch_stock_daily

        # Provide data in descending order
        reversed_df = SAMPLE_DAILY_DF.iloc[::-1].reset_index(drop=True)
        mock_ak.stock_zh_a_hist.return_value = reversed_df.copy()

        result = fetch_stock_daily("000001", "20240101", "20240131")

        assert result["date"].is_monotonic_increasing


class TestFetcherMarket:
    """_classify_market helper."""

    def test_shanghai(self):
        from app.data.fetcher import _classify_market
        assert _classify_market("600000") == "sh"
        assert _classify_market("601398") == "sh"

    def test_shenzhen(self):
        from app.data.fetcher import _classify_market
        assert _classify_market("000001") == "sz"
        assert _classify_market("300750") == "sz"

    def test_beijing(self):
        from app.data.fetcher import _classify_market
        assert _classify_market("830799") == "bj"
        assert _classify_market("430047") == "bj"
