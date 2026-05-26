"""Backtest service stub — will be implemented in step 2-3."""

import json
from sqlalchemy.orm import Session
from ..models.backtest import BacktestResult


def create_backtest(db: Session, strategy: str, params: dict, start_date: str, end_date: str) -> BacktestResult:
    """Create a new backtest record (stub — no actual backtesting yet)."""
    result = BacktestResult(
        strategy_name=strategy,
        params_json=json.dumps(params),
        start_date=start_date,
        end_date=end_date,
        status="pending",
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
