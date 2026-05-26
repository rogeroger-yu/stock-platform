"""Daily Simulation API — 每日大盘模拟接口。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from ..services.daily_simulation import run_daily_simulation, format_daily_report
from ..paper_trade.engine import PaperTradeEngine

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# Shared paper engine
_engine = PaperTradeEngine(initial_capital=1_000_000.0)


class SimulationRequest(BaseModel):
    as_of_date: Optional[str] = None
    symbols: list[str] = Field(default_factory=lambda: [
        "000001", "600000", "000858", "600519", "002594"
    ])
    auto_execute: bool = False


@router.post("/daily")
async def daily_simulation(req: SimulationRequest):
    """运行每日大盘模拟。

    检查所有策略在跟踪标的上的信号，生成报告。
    如果 auto_execute=True，自动执行 Top 买入信号的模拟交易。
    """
    engine = _engine if req.auto_execute else None
    result = run_daily_simulation(
        as_of_date=req.as_of_date,
        symbols=req.symbols,
        paper_engine=engine,
    )
    report = format_daily_report(result)
    return {
        **result,
        "report": report,
    }


@router.get("/report")
async def daily_report():
    """快速获取今日模拟报告。"""
    result = run_daily_simulation()
    report = format_daily_report(result)
    return {
        "date": result["date"],
        "report": report,
        "summary": {
            "signals": result["total_signals"],
            "buy": result["buy_signals_count"],
            "sell": result["sell_signals_count"],
        },
    }
