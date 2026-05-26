"""Paper Trade API router — 模拟交易接口 + 策略桥接。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.paper_trade.engine import (
    PaperTradeEngine,
    OrderSide,
    OrderStatus,
    signals_to_orders,
)
from app.paper_trade.bridge import BacktestTradeBridge

router = APIRouter(prefix="/api/paper", tags=["paper_trade"])

# Global instances
_engine = PaperTradeEngine(initial_capital=1_000_000.0)
_bridge = BacktestTradeBridge(_engine)


# ─── Schemas ────────────────────────────────────────────────────────


class OrderRequest(BaseModel):
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float


class SignalRequest(BaseModel):
    signals: dict[str, int]  # symbol -> signal
    prices: dict[str, float]  # symbol -> current_price


class ActivateStrategyRequest(BaseModel):
    strategy_type: str
    params: dict = Field(default_factory=dict)
    symbols: list[str]


class DailyCheckRequest(BaseModel):
    as_of_date: Optional[str] = None
    auto_execute: bool = False  # If True, automatically execute suggested orders


# ─── Paper Trade Endpoints ─────────────────────────────────────────


@router.post("/order")
async def place_order(req: OrderRequest):
    """下单（模拟）。"""
    side = OrderSide(req.side)
    order = _engine.place_order(req.symbol, side, req.quantity, req.price)
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "filled_price": order.filled_price,
        "filled_quantity": order.filled_quantity,
        "commission": order.commission,
    }


@router.get("/account")
async def get_account():
    """查询账户状态。"""
    account = _engine.get_account()
    return {
        "account_id": account.account_id,
        "cash": account.cash,
        "total_value": account.total_value,
        "total_pnl": account.total_pnl,
        "positions": {
            sym: {
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
            }
            for sym, pos in account.positions.items()
        },
    }


@router.get("/positions")
async def get_positions():
    """查询持仓。"""
    positions = _engine.get_positions()
    return {
        sym: {
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "current_price": pos.current_price,
            "unrealized_pnl": pos.unrealized_pnl,
        }
        for sym, pos in positions.items()
    }


@router.get("/orders")
async def get_orders(status: Optional[str] = None):
    """查询订单。"""
    s = OrderStatus(status) if status else None
    orders = _engine.get_orders(s)
    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side.value,
            "quantity": o.quantity,
            "price": o.price,
            "filled_price": o.filled_price,
            "status": o.status.value,
            "commission": o.commission,
            "created_at": o.created_at,
        }
        for o in orders
    ]


@router.get("/trades")
async def get_trades():
    """查询交易记录。"""
    return _engine.get_trade_log()


@router.post("/signals")
async def process_signals(req: SignalRequest):
    """将策略信号转换为订单建议（不自动下单）。"""
    account = _engine.get_account()
    suggestions = signals_to_orders(req.signals, req.prices, account)
    return {"suggestions": suggestions, "account_cash": account.cash}


@router.post("/reset")
async def reset_account():
    """重置模拟账户。"""
    global _engine, _bridge
    _engine = PaperTradeEngine(initial_capital=1_000_000.0)
    _bridge = BacktestTradeBridge(_engine)
    return {"status": "ok", "message": "账户已重置"}


# ─── Strategy Bridge Endpoints ─────────────────────────────────────


@router.post("/strategies/activate")
async def activate_strategy(req: ActivateStrategyRequest):
    """激活策略，开始监控信号。

    策略将被加入监控列表，每日检查信号变化。
    """
    result = _bridge.activate_strategy(
        strategy_type=req.strategy_type,
        params=req.params,
        symbols=req.symbols,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/strategies/{strategy_type}")
async def deactivate_strategy(strategy_type: str):
    """停用策略。"""
    return _bridge.deactivate_strategy(strategy_type)


@router.get("/strategies/active")
async def list_active_strategies():
    """列出已激活的策略。"""
    return _bridge.get_active_strategies()


@router.post("/daily-check")
async def daily_check(req: DailyCheckRequest):
    """执行每日信号检查。

    检查所有已激活策略的最新信号，生成订单建议。
    如果 auto_execute=True，将自动执行建议订单。
    """
    result = _bridge.run_daily_check(req.as_of_date)

    if req.auto_execute and result["orders_suggested"]:
        executions = _bridge.execute_suggested_orders(result["orders_suggested"])
        result["executions"] = executions
        result["auto_executed"] = True

    return result


@router.get("/signal-history")
async def get_signal_history(limit: int = 100):
    """查询信号历史。"""
    return _bridge.get_signal_history(limit)


@router.post("/compare")
async def backtest_vs_live(strategy_type: str, params: dict, symbols: list[str]):
    """对比回测结果 vs 模拟交易表现。"""
    result = _bridge.backtest_vs_live(strategy_type, params, symbols)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
