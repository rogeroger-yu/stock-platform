from fastapi import APIRouter, HTTPException
from app.models.schemas import StrategyConfig

router = APIRouter(tags=["strategies"])

# In-memory mock store
_strategies: dict[str, StrategyConfig] = {}


@router.get("/strategies")
async def list_strategies():
    return list(_strategies.values())


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategies[strategy_id]


@router.post("/strategies")
async def create_strategy(config: StrategyConfig):
    _strategies[config.id] = config
    return config


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    del _strategies[strategy_id]
    return {"status": "deleted"}
