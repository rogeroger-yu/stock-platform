"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field
from datetime import date


class StrategyConfig(BaseModel):
    id: str = Field(..., description="Unique strategy identifier")
    name: str = Field(..., description="Human-readable strategy name")
    description: str = ""
    strategy_type: str = Field(..., description="Strategy class type")
    params: dict = Field(default_factory=dict, description="Strategy parameters")
    symbols: list[str] = Field(default_factory=list, description="Target symbols")
    start_date: date | None = None
    end_date: date | None = None


class BacktestRequest(BaseModel):
    strategy_id: str
    start_date: date
    end_date: date
    initial_capital: float = 1_000_000.0
    commission: float = 0.001


class EquityCurvePoint(BaseModel):
    date: date
    equity: float
    benchmark: float | None = None


class BacktestResult(BaseModel):
    strategy_id: str
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    equity_curve: list[EquityCurvePoint]


class CompareRequest(BaseModel):
    strategy_ids: list[str]
    start_date: date
    end_date: date


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
