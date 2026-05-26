"""Strategy CRUD API — persistent strategies with create, update, delete, list."""

import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.strategy import Strategy

router = APIRouter(prefix="/api", tags=["strategies"])


# ─── Request/Response Schemas ───────────────────────────────────────


class StrategyCreate(BaseModel):
    """Create a new strategy."""
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(..., description="Strategy class key")
    description: str = ""
    params: dict = Field(default_factory=dict)
    symbols: list[str] = Field(default_factory=list)


class StrategyUpdate(BaseModel):
    """Update an existing strategy's params or metadata."""
    name: str | None = None
    description: str | None = None
    params: dict | None = None
    symbols: list[str] | None = None


class StrategyOut(BaseModel):
    """Strategy response."""
    id: int
    name: str
    strategy_type: str
    description: str
    params: dict
    symbols: list[str]
    last_annual_return: float | None = None
    last_sharpe: float | None = None
    last_max_drawdown: float | None = None
    last_win_rate: float | None = None
    backtest_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


def _to_out(s: Strategy) -> StrategyOut:
    return StrategyOut(
        id=s.id,
        name=s.name,
        strategy_type=s.strategy_type,
        description=s.description,
        params=json.loads(s.params_json) if s.params_json else {},
        symbols=json.loads(s.symbols_json) if s.symbols_json else [],
        last_annual_return=s.last_annual_return,
        last_sharpe=s.last_sharpe,
        last_max_drawdown=s.last_max_drawdown,
        last_win_rate=s.last_win_rate,
        backtest_count=s.backtest_count,
        created_at=s.created_at.isoformat() if s.created_at else None,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


# ─── Endpoints ─────────────────────────────────────────────────────


@router.get("/strategies")
async def list_strategies(
    strategy_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[StrategyOut]:
    """List all strategies, optionally filtered by type."""
    query = db.query(Strategy)
    if strategy_type:
        query = query.filter(Strategy.strategy_type == strategy_type)
    return [_to_out(s) for s in query.order_by(Strategy.updated_at.desc()).all()]


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)) -> StrategyOut:
    """Get a single strategy by ID."""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _to_out(s)


@router.post("/strategies", status_code=201)
async def create_strategy(
    req: StrategyCreate, db: Session = Depends(get_db)
) -> StrategyOut:
    """Create a new strategy."""
    # Check name uniqueness
    existing = db.query(Strategy).filter(Strategy.name == req.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Strategy '{req.name}' already exists")

    s = Strategy(
        name=req.name,
        strategy_type=req.strategy_type,
        description=req.description,
        params_json=json.dumps(req.params, ensure_ascii=False),
        symbols_json=json.dumps(req.symbols, ensure_ascii=False),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    req: StrategyUpdate,
    db: Session = Depends(get_db),
) -> StrategyOut:
    """Update an existing strategy's parameters, name, or description."""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if req.name is not None:
        # Check new name doesn't collide
        dup = db.query(Strategy).filter(
            Strategy.name == req.name, Strategy.id != strategy_id
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail=f"Name '{req.name}' already taken")
        s.name = req.name

    if req.description is not None:
        s.description = req.description
    if req.params is not None:
        s.params_json = json.dumps(req.params, ensure_ascii=False)
    if req.symbols is not None:
        s.symbols_json = json.dumps(req.symbols, ensure_ascii=False)

    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Delete a strategy."""
    s = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(s)
    db.commit()
    return {"status": "deleted", "id": strategy_id}
