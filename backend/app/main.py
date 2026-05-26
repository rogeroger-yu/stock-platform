from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.strategies import router as strategies_router
from app.api.backtests import router as backtests_router

app = FastAPI(title="Stock Strategy Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(strategies_router, prefix="/api")
app.include_router(backtests_router, prefix="/api")
