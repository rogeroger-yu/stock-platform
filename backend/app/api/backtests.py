from fastapi import APIRouter
from app.models.schemas import BacktestRequest, BacktestResult

router = APIRouter(tags=["backtests"])


@router.post("/backtests/run")
async def run_backtest(request: BacktestRequest) -> BacktestResult:
    """Run a backtest for a given strategy. Stub implementation."""
    return BacktestResult(
        strategy_id=request.strategy_id,
        total_return=0.0,
        annualized_return=0.0,
        sharpe_ratio=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        total_trades=0,
        equity_curve=[],
    )
