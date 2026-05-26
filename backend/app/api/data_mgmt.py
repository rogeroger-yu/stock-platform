"""Data management API — list available stocks, check coverage, download data."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..data.store import list_available_stocks, get_data_coverage
from ..data.downloader import download_all

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/stocks")
async def get_available_stocks() -> list[dict]:
    """List all locally available stock data with coverage info."""
    stocks = list_available_stocks()
    result = []
    for sym in stocks:
        try:
            cov = get_data_coverage(sym)
            result.append({
                "symbol": sym,
                "start": cov["start"],
                "end": cov["end"],
                "rows": cov["rows"],
                "missing_pct": cov["missing_pct"],
            })
        except Exception:
            result.append({"symbol": sym, "error": "failed to read"})
    return result


@router.get("/stocks/{symbol}")
async def get_stock_coverage(symbol: str) -> dict:
    """Get data coverage for a single stock."""
    try:
        cov = get_data_coverage(symbol)
        return {
            "symbol": symbol,
            **cov,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")


class DownloadRequest(BaseModel):
    symbols: list[str]
    start_date: str = "20150101"
    end_date: str = "20250501"


@router.post("/download")
async def download_data(req: DownloadRequest):
    """Download stock data for given symbols."""
    from ..data.fetcher import fetch_stock_daily
    from ..data.store import save_stock_daily
    import time

    results = []
    for sym in req.symbols:
        try:
            df = fetch_stock_daily(sym, req.start_date, req.end_date)
            path = save_stock_daily(df, sym)
            results.append({"symbol": sym, "rows": len(df), "path": path, "status": "ok"})
        except Exception as e:
            results.append({"symbol": sym, "status": "error", "error": str(e)})
        time.sleep(0.3)
    return {
        "downloaded": sum(1 for r in results if r["status"] == "ok"),
        "failed": sum(1 for r in results if r["status"] != "ok"),
        "results": results,
    }
