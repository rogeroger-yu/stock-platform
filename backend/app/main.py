"""Stock Strategy Platform — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.strategies import router as strategies_router
from app.api.strategy_types import router as strategy_types_router
from app.api.backtests import router as backtests_router
from app.api.simulation import router as simulation_router
from app.paper_trade.api import router as paper_trade_router
from app.db import init_db

app = FastAPI(title="Stock Strategy Platform", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://47.97.26.218:5173",
        "https://rogeroger-yu.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(strategy_types_router)
app.include_router(strategies_router)
app.include_router(backtests_router)
app.include_router(simulation_router)
app.include_router(paper_trade_router)


@app.on_event("startup")
def on_startup():
    init_db()
