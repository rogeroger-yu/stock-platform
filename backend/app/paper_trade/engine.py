"""Paper Trade Bridge — 模拟交易桥接层。

提供统一接口对接 vnpy/QMT 模拟盘，不接真账户。

核心功能：
1. 模拟下单（buy/sell）
2. 持仓查询
3. 账户余额查询
4. 交易记录查询
5. 从回测信号到模拟订单的转换

安全约束：
- 仅连接模拟账户
- 不接受真钱下单
- 不存储券商 API key
"""

from __future__ import annotations

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PaperTradeMode(str, Enum):
    """模拟交易模式。"""
    SIMULATED = "simulated"  # 纯本地模拟（默认）
    VNPY = "vnpy"           # vnpy 模拟盘
    QMT = "qmt"             # QMT 模拟盘


@dataclass
class Order:
    """模拟订单。"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: int = 0
    price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_quantity: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    filled_at: Optional[str] = None
    commission: float = 0.0


@dataclass
class Position:
    """持仓。"""
    symbol: str = ""
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class Account:
    """模拟账户。"""
    account_id: str = "paper_account"
    cash: float = 1_000_000.0
    total_value: float = 1_000_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    total_pnl: float = 0.0


class PaperTradeEngine:
    """模拟交易引擎。

    提供纯本地模拟，不连接任何真实券商。
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.account = Account(cash=initial_capital, total_value=initial_capital)
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.orders: list[Order] = []
        self.trade_log: list[dict] = []

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float,
    ) -> Order:
        """下单。

        Args:
            symbol: 股票代码
            side: 买入/卖出
            quantity: 数量
            price: 限价

        Returns:
            Order 对象
        """
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        # 验证
        if quantity <= 0:
            order.status = OrderStatus.REJECTED
            self.orders.append(order)
            return order

        if side == OrderSide.BUY:
            # 检查资金是否足够
            total_cost = quantity * price * (1 + self.commission_rate + self.slippage_rate)
            if total_cost > self.account.cash:
                order.status = OrderStatus.REJECTED
                self.orders.append(order)
                return order
        elif side == OrderSide.SELL:
            # 检查是否有足够持仓
            pos = self.account.positions.get(symbol)
            if not pos or pos.quantity < quantity:
                order.status = OrderStatus.REJECTED
                self.orders.append(order)
                return order

        # 模拟成交
        self._fill_order(order)
        self.orders.append(order)
        return order

    def _fill_order(self, order: Order) -> None:
        """模拟订单成交。"""
        # 应用滑点
        if order.side == OrderSide.BUY:
            fill_price = order.price * (1 + self.slippage_rate)
        else:
            fill_price = order.price * (1 - self.slippage_rate)

        commission = order.quantity * fill_price * self.commission_rate

        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now().isoformat()

        # 更新账户
        if order.side == OrderSide.BUY:
            cost = order.quantity * fill_price + commission
            self.account.cash -= cost

            # 更新持仓
            if order.symbol in self.account.positions:
                pos = self.account.positions[order.symbol]
                total_cost = pos.avg_cost * pos.quantity + fill_price * order.quantity
                pos.quantity += order.quantity
                pos.avg_cost = total_cost / pos.quantity
            else:
                self.account.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_cost=fill_price,
                )
        else:  # SELL
            revenue = order.quantity * fill_price - commission
            self.account.cash += revenue

            pos = self.account.positions[order.symbol]
            pnl = (fill_price - pos.avg_cost) * order.quantity - commission
            pos.quantity -= order.quantity

            if pos.quantity == 0:
                del self.account.positions[order.symbol]

            self.account.total_pnl += pnl

        # 记录交易
        self.trade_log.append({
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "filled_price": fill_price,
            "commission": commission,
            "timestamp": order.filled_at,
        })

    def get_account(self) -> Account:
        """获取账户状态。"""
        # 更新总市值
        total_position_value = sum(
            pos.quantity * pos.current_price
            for pos in self.account.positions.values()
        )
        self.account.total_value = self.account.cash + total_position_value
        return self.account

    def get_positions(self) -> dict[str, Position]:
        """获取所有持仓。"""
        return self.account.positions.copy()

    def get_orders(self, status: Optional[OrderStatus] = None) -> list[Order]:
        """获取订单列表。"""
        if status:
            return [o for o in self.orders if o.status == status]
        return self.orders.copy()

    def get_trade_log(self) -> list[dict]:
        """获取交易记录。"""
        return self.trade_log.copy()

    def update_prices(self, prices: dict[str, float]) -> None:
        """更新持仓市价。"""
        for symbol, price in prices.items():
            if symbol in self.account.positions:
                pos = self.account.positions[symbol]
                pos.current_price = price
                pos.market_value = pos.quantity * price
                pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity


def signals_to_orders(
    signals: dict[str, int],  # symbol -> signal (1=buy, -1=sell, 0=hold)
    current_prices: dict[str, float],
    account: Account,
    max_position_pct: float = 0.2,  # 单只股票最大仓位占比
) -> list[dict]:
    """将策略信号转换为模拟订单建议。

    不直接下单，返回订单建议列表供审核。

    Args:
        signals: {symbol: signal} 信号映射
        current_prices: {symbol: price} 当前价格
        account: 当前账户状态
        max_position_pct: 单只股票最大仓位占比

    Returns:
        订单建议列表 [{symbol, side, quantity, price, reason}]
    """
    orders = []
    total_value = account.total_value
    max_per_stock = total_value * max_position_pct

    for symbol, signal in signals.items():
        price = current_prices.get(symbol, 0)
        if price <= 0:
            continue

        if signal == 1 and symbol not in account.positions:
            # 买入建议
            quantity = int(max_per_stock / price)
            if quantity > 0 and account.cash >= quantity * price:
                orders.append({
                    "symbol": symbol,
                    "side": "buy",
                    "quantity": quantity,
                    "price": price,
                    "reason": f"策略信号买入，预计成本 {quantity * price:,.0f}",
                })

        elif signal == -1 and symbol in account.positions:
            # 卖出建议
            pos = account.positions[symbol]
            orders.append({
                "symbol": symbol,
                "side": "sell",
                "quantity": pos.quantity,
                "price": price,
                "reason": f"策略信号卖出，持仓 {pos.quantity} 股",
            })

    return orders
