"""Strategy API — list available strategy types + seed defaults."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..strategies import list_strategy_types
from ..models.strategy import Strategy

router = APIRouter(prefix="/api", tags=["strategy-types"])


@router.get("/strategy-types")
async def get_strategy_types() -> list[dict]:
    """List all available strategy class types with default parameters.

    This is the "strategy catalog" — what strategies can be instantiated.
    """
    return list_strategy_types()


@router.post("/strategies/seed-defaults")
async def seed_default_strategies(db: Session = Depends(get_db)):
    """Seed the database with one instance of each built-in strategy type.

    Useful for first-time setup. Skips strategies that already exist.
    """
    types = list_strategy_types()
    created = []
    skipped = []

    for t in types:
        existing = db.query(Strategy).filter(Strategy.strategy_type == t["type"]).first()
        if existing:
            skipped.append(t["type"])
            continue

        s = Strategy(
            name=t["name"],
            strategy_type=t["type"],
            description=f"Default {t['name']} strategy",
            params_json=__import__("json").dumps(t["default_params"], ensure_ascii=False),
            symbols_json="[]",
        )
        db.add(s)
        created.append(t["type"])

    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "total": len(types),
    }
