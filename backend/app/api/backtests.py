"""Backtest API — run backtests, list results, compare strategies, batch ranking."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import date
import json

from ..db import get_db
from ..models.backtest import BacktestResult as BacktestResultDB
from ..models.strategy import Strategy as StrategyDB
from ..core.backtest_engine import BacktestEngine
from ..core.walk_forward import walk_forward_single, WFBenchmark
from ..data.store import load_stock_daily
from ..strategies import get_strategy_class

router = APIRouter(prefix="/api", tags=["backtests"])


# ─── Schemas ────────────────────────────────────────────────────────


class RunBacktestRequest(BaseModel):
    strategy_id: int
    symbols: list[str] = Field(..., description="Stock codes to backtest")
    start_date: date
    end_date: date
    initial_capital: float = 1_000_000.0
    commission: float = 0.001
    slippage: float = 0.0005
    param_overrides: dict = Field(default_factory=dict, description="Override strategy params for this run")


class BatchRunRequest(BaseModel):
    """Run all strategies across multiple symbols and time periods."""
    symbols: list[str] = Field(default_factory=lambda: ["000001", "600519", "000858"])
    start_date: date = date(2020, 1, 1)
    end_date: date = date(2025, 5, 1)
    initial_capital: float = 1_000_000.0
    top_n: int = 10


class CompareRequest(BaseModel):
    backtest_ids: list[int]


class WalkForwardRequest(BaseModel):
    strategy_id: int
    symbol: str
    is_start: str = "2015-01-01"
    is_end: str = "2020-12-31"
    oos_start: str = "2021-01-01"
    oos_end: str = "2025-05-01"
    param_grid: dict = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    id: int
    strategy_name: str
    strategy_type: str
    params: dict
    symbols: list[str]
    start_date: str
    end_date: str
    total_return: float
    annualized_return: float
    sharpe: float
    max_drawdown: float
    calmar: float
    num_trades: int
    win_rate: float
    avg_holding_days: float
    equity_curve: list
    monthly_returns: list
    yearly_returns: list


# ─── Helpers ────────────────────────────────────────────────────────


def _load_data(symbols: list[str], start: str, end: str) -> dict[str, any]:
    """Load OHLCV data for symbols, filtering by date range."""
    data = {}
    for sym in symbols:
        try:
            df = load_stock_daily(sym)
            df["date"] = __import__("pandas").to_datetime(df["date"])
            mask = (df["date"] >= start) & (df["date"] <= end)
            df = df[mask].copy()
            if not df.empty:
                data[sym] = df
        except FileNotFoundError:
            continue
    return data


def _save_backtest_result(
    db: Session,
    strategy_name: str,
    strategy_type: str,
    params: dict,
    symbols: list[str],
    start_date: str,
    end_date: str,
    metrics: dict,
) -> int:
    """Persist backtest result and return its ID."""
    record = BacktestResultDB(
        strategy_name=strategy_name,
        params_json=json.dumps({
            "strategy_type": strategy_type,
            "params": params,
            "symbols": symbols,
        }),
        start_date=start_date,
        end_date=end_date,
        annual_return=metrics.get("annualized_return", 0),
        max_drawdown=metrics.get("max_drawdown", 0),
        sharpe_ratio=metrics.get("sharpe", 0),
        equity_curve_json=json.dumps(metrics.get("equity_curve", []), default=str),
        status="completed",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


# ─── Endpoints ─────────────────────────────────────────────────────


@router.post("/backtests/run")
async def run_backtest(
    req: RunBacktestRequest, db: Session = Depends(get_db)
) -> BacktestResponse:
    """Run a backtest for a single strategy on one or more symbols."""
    # Load strategy from DB
    strategy_record = db.query(StrategyDB).filter(StrategyDB.id == req.strategy_id).first()
    if not strategy_record:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy_class = get_strategy_class(strategy_record.strategy_type)
    if not strategy_class:
        raise HTTPException(status_code=400, detail=f"Unknown strategy type: {strategy_record.strategy_type}")

    # Merge params: DB defaults + overrides
    params = json.loads(strategy_record.params_json) if strategy_record.params_json else {}
    params.update(req.param_overrides)
    strategy = strategy_class(**params)

    # Load data
    data_dict = _load_data(req.symbols, str(req.start_date), str(req.end_date))
    if not data_dict:
        raise HTTPException(status_code=400, detail="No data available for given symbols/dates")

    engine = BacktestEngine(
        initial_capital=req.initial_capital,
        commission=req.commission,
        slippage=req.slippage,
    )

    # Single or multi-stock
    if len(data_dict) == 1:
        symbol, df = next(iter(data_dict.items()))
        result = engine.run_single(strategy, df, symbol)
        result_dict = result.to_dict()
    else:
        from ..core.portfolio import PortfolioEngine
        pf = PortfolioEngine(
            initial_capital=req.initial_capital,
            commission=req.commission,
            slippage=req.slippage,
        )
        result = pf.run(strategy, data_dict)
        result_dict = result.to_dict()

    # Persist
    bt_id = _save_backtest_result(
        db,
        strategy_name=strategy_record.name,
        strategy_type=strategy_record.strategy_type,
        params=params,
        symbols=list(data_dict.keys()),
        start_date=str(req.start_date),
        end_date=str(req.end_date),
        metrics=result_dict,
    )

    # Update strategy's last metrics
    strategy_record.last_annual_return = result_dict.get("annualized_return", 0)
    strategy_record.last_sharpe = result_dict.get("sharpe", 0)
    strategy_record.last_max_drawdown = result_dict.get("max_drawdown", 0)
    strategy_record.last_win_rate = result_dict.get("win_rate", 0)
    strategy_record.backtest_count = (strategy_record.backtest_count or 0) + 1
    db.commit()

    return BacktestResponse(
        id=bt_id,
        strategy_name=strategy_record.name,
        strategy_type=strategy_record.strategy_type,
        params=params,
        symbols=list(data_dict.keys()),
        start_date=str(req.start_date),
        end_date=str(req.end_date),
        total_return=result_dict.get("total_return", 0),
        annualized_return=result_dict.get("annualized_return", 0),
        sharpe=result_dict.get("sharpe", 0),
        max_drawdown=result_dict.get("max_drawdown", 0),
        calmar=result_dict.get("calmar", 0),
        num_trades=result_dict.get("num_trades", 0),
        win_rate=result_dict.get("win_rate", 0),
        avg_holding_days=result_dict.get("avg_holding_days", 0),
        equity_curve=result_dict.get("equity_curve", []),
        monthly_returns=result_dict.get("monthly_returns", []),
        yearly_returns=result_dict.get("yearly_returns", []),
    )


@router.post("/backtests/batch")
async def batch_run(
    req: BatchRunRequest, db: Session = Depends(get_db)
) -> dict:
    """Run ALL registered strategies across symbols, return Top N ranked by composite score.

    Composite score = weighted combination of:
    - Annualized return (40%)
    - Sharpe ratio (30%)
    - Max drawdown penalty (30%, lower is better)
    """
    strategies = db.query(StrategyDB).all()
    if not strategies:
        raise HTTPException(status_code=400, detail="No strategies registered")

    data_dict = _load_data(req.symbols, str(req.start_date), str(req.end_date))
    if not data_dict:
        raise HTTPException(status_code=400, detail="No data for given symbols/dates")

    results = []

    for strat_record in strategies:
        try:
            strategy_class = get_strategy_class(strat_record.strategy_type)
            if not strategy_class:
                continue
            params = json.loads(strat_record.params_json) if strat_record.params_json else {}
            strategy = strategy_class(**params)

            engine = BacktestEngine(initial_capital=req.initial_capital)

            if len(data_dict) == 1:
                symbol, df = next(iter(data_dict.items()))
                bt = engine.run_single(strategy, df, symbol)
                d = bt.to_dict()
            else:
                from ..core.portfolio import PortfolioEngine
                pf = PortfolioEngine(initial_capital=req.initial_capital)
                bt = pf.run(strategy, data_dict)
                d = bt.to_dict()

            # Composite score: 0.4 * norm(ann_ret) + 0.3 * norm(sharpe) + 0.3 * (1 - mdd)
            ann_ret = d.get("annualized_return", 0)
            sharpe = d.get("sharpe", 0)
            mdd = d.get("max_drawdown", 1)
            win_rate = d.get("win_rate", 0)

            # Simple composite
            score = 0.40 * ann_ret + 0.30 * sharpe + 0.30 * (1 - mdd)

            results.append({
                "strategy_id": strat_record.id,
                "strategy_name": strat_record.name,
                "strategy_type": strat_record.strategy_type,
                "params": params,
                "total_return": round(d.get("total_return", 0), 4),
                "annualized_return": round(ann_ret, 4),
                "sharpe": round(sharpe, 4),
                "max_drawdown": round(mdd, 4),
                "win_rate": round(win_rate, 4),
                "num_trades": d.get("num_trades", 0),
                "composite_score": round(score, 4),
            })

            # Update strategy metrics
            strat_record.last_annual_return = ann_ret
            strat_record.last_sharpe = sharpe
            strat_record.last_max_drawdown = mdd
            strat_record.last_win_rate = win_rate
            strat_record.backtest_count = (strat_record.backtest_count or 0) + 1

        except Exception as e:
            results.append({
                "strategy_id": strat_record.id,
                "strategy_name": strat_record.name,
                "error": str(e),
                "composite_score": -999,
            })

    db.commit()

    # Sort by composite score, take top N
    results.sort(key=lambda x: x.get("composite_score", -999), reverse=True)
    top_results = results[:req.top_n]

    return {
        "total_strategies": len(strategies),
        "symbols": req.symbols,
        "period": f"{req.start_date} ~ {req.end_date}",
        "top_n": req.top_n,
        "rankings": top_results,
        "all_scores": [{"name": r["strategy_name"], "score": r.get("composite_score", -999)} for r in results],
    }


@router.post("/backtests/walk-forward")
async def walk_forward(
    req: WalkForwardRequest, db: Session = Depends(get_db)
) -> dict:
    """Run walk-forward optimization for a strategy on a single symbol."""
    strat_record = db.query(StrategyDB).filter(StrategyDB.id == req.strategy_id).first()
    if not strat_record:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy_class = get_strategy_class(strat_record.strategy_type)
    if not strategy_class:
        raise HTTPException(status_code=400, detail=f"Unknown type: {strat_record.strategy_type}")

    # Load full data
    try:
        df = load_stock_daily(req.symbol)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"No data for {req.symbol}")

    # Default param grid if not provided
    param_grid = req.param_grid
    if not param_grid:
        defaults = json.loads(strat_record.params_json) if strat_record.params_json else {}
        # Auto-generate grid from numeric params
        param_grid = {}
        for k, v in defaults.items():
            if isinstance(v, (int, float)):
                if k.endswith("window") or k.endswith("period"):
                    param_grid[k] = [int(v * 0.7), int(v), int(v * 1.5)]
                elif isinstance(v, float):
                    param_grid[k] = [v * 0.8, v, v * 1.2]
                else:
                    param_grid[k] = [v]

    if not param_grid:
        raise HTTPException(status_code=400, detail="Cannot generate param grid; provide param_grid explicitly")

    wf_result = walk_forward_single(
        strategy_class=strategy_class,
        param_grid=param_grid,
        data=df,
        is_start=req.is_start,
        is_end=req.is_end,
        oos_start=req.oos_start,
        oos_end=req.oos_end,
        symbol=req.symbol,
    )

    return wf_result.to_dict()


@router.get("/backtests")
async def list_backtests(
    limit: int = 50, db: Session = Depends(get_db)
) -> list[dict]:
    """List recent backtest results."""
    rows = db.query(BacktestResultDB).order_by(BacktestResultDB.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "strategy_name": r.strategy_name,
            "strategy_type": (json.loads(r.params_json) if r.params_json else {}).get("strategy_type", ""),
            "params": {k: v for k, v in (json.loads(r.params_json) if r.params_json else {}).items() if k != "strategy_type"},
            "start_date": r.start_date,
            "end_date": r.end_date,
            "annual_return": r.annual_return,
            "max_drawdown": r.max_drawdown,
            "sharpe_ratio": r.sharpe_ratio,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: int, db: Session = Depends(get_db)) -> dict:
    """Get a single backtest result."""
    r = db.query(BacktestResultDB).filter(BacktestResultDB.id == backtest_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {
        "id": r.id,
        "strategy_name": r.strategy_name,
        "strategy_type": params.get("strategy_type", ""),
        "params": {k: v for k, v in params.items() if k != "strategy_type"},
        "symbols": params.get("symbols", []),
        "start_date": r.start_date,
        "end_date": r.end_date,
        "annual_return": r.annual_return,
        "max_drawdown": r.max_drawdown,
        "sharpe_ratio": r.sharpe_ratio,
        "equity_curve": json.loads(r.equity_curve_json) if r.equity_curve_json else [],
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("/backtests/compare")
async def compare_backtests(
    req: CompareRequest, db: Session = Depends(get_db)
) -> list[dict]:
    """Compare multiple backtest results side by side."""
    results = []
    for bid in req.backtest_ids:
        r = db.query(BacktestResultDB).filter(BacktestResultDB.id == bid).first()
        if r:
            results.append({
                "id": r.id,
                "strategy_name": r.strategy_name,
                "params": json.loads(r.params_json) if r.params_json else {},
                "start_date": r.start_date,
                "end_date": r.end_date,
                "annual_return": r.annual_return,
                "max_drawdown": r.max_drawdown,
                "sharpe_ratio": r.sharpe_ratio,
                "equity_curve": json.loads(r.equity_curve_json) if r.equity_curve_json else [],
            })
    return results
