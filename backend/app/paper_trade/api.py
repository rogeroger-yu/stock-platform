"""Paper Trade API router — 模拟交易接口。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.paper_trade.engine import (
    PaperTradeEngine,
    OrderSide,
    OrderStatus,
    signals_to_orders,
)

router = APIRouter(prefix="/api/paper", tags=["paper_trade"])

# Global engine instance (simulated account)
_engine = PaperTradeEngine(initial_capital=1_000_000.0)


class OrderRequest(BaseModel):
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float


class SignalRequest(BaseModel):
    signals: dict[str, int]  # symbol -> signal
    prices: dict[str, float]  # symbol -> current_price


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
    global _engine
    _engine = PaperTradeEngine(initial_capital=1_000_000.0)
    return {"status": "ok", "message": "账户已重置"}
