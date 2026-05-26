import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.backtest import BacktestResult

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy: str
    params: dict = {}
    start_date: str = "2015-01-01"
    end_date: str = "2024-12-31"


@router.post("/run")
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    result = BacktestResult(
        strategy_name=req.strategy,
        params_json=json.dumps(req.params),
        start_date=req.start_date,
        end_date=req.end_date,
        status="pending",
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return {"id": result.id, "status": result.status}


@router.get("/{backtest_id}")
async def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    result = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {
        "id": result.id,
        "strategy_name": result.strategy_name,
        "params_json": result.params_json,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "annual_return": result.annual_return,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "equity_curve_json": result.equity_curve_json,
        "status": result.status,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }
