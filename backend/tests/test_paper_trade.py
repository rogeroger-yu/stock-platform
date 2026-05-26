"""Tests for paper trade engine."""

import pytest
from app.paper_trade.engine import (
    PaperTradeEngine,
    OrderSide,
    OrderStatus,
    Account,
    signals_to_orders,
)


class TestPaperTradeEngine:
    def test_initial_account(self):
        engine = PaperTradeEngine(initial_capital=500_000)
        account = engine.get_account()
        assert account.cash == 500_000
        assert account.total_value == 500_000
        assert len(account.positions) == 0

    def test_buy_order(self):
        engine = PaperTradeEngine(initial_capital=1_000_000, commission_rate=0.001, slippage_rate=0.0005)
        order = engine.place_order("000001", OrderSide.BUY, 1000, 10.0)

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 1000
        assert order.filled_price > 10.0  # slippage applied
        assert "000001" in engine.get_positions()
        assert engine.get_account().cash < 1_000_000

    def test_sell_order(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        engine.place_order("000001", OrderSide.BUY, 1000, 10.0)
        order = engine.place_order("000001", OrderSide.SELL, 1000, 11.0)

        assert order.status == OrderStatus.FILLED
        assert "000001" not in engine.get_positions()

    def test_insufficient_funds(self):
        engine = PaperTradeEngine(initial_capital=1000)
        order = engine.place_order("000001", OrderSide.BUY, 1000, 10.0)  # needs 10000+

        assert order.status == OrderStatus.REJECTED

    def test_insufficient_position(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        order = engine.place_order("000001", OrderSide.SELL, 1000, 10.0)

        assert order.status == OrderStatus.REJECTED

    def test_invalid_quantity(self):
        engine = PaperTradeEngine()
        order = engine.place_order("000001", OrderSide.BUY, 0, 10.0)
        assert order.status == OrderStatus.REJECTED

    def test_trade_log(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        engine.place_order("000001", OrderSide.BUY, 100, 10.0)
        engine.place_order("000001", OrderSide.SELL, 100, 11.0)

        log = engine.get_trade_log()
        assert len(log) == 2
        assert log[0]["side"] == "buy"
        assert log[1]["side"] == "sell"

    def test_update_prices(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        engine.place_order("000001", OrderSide.BUY, 1000, 10.0)
        engine.update_prices({"000001": 12.0})

        pos = engine.get_positions()["000001"]
        assert pos.current_price == 12.0
        assert pos.unrealized_pnl > 0

    def test_commission_deducted(self):
        engine = PaperTradeEngine(initial_capital=1_000_000, commission_rate=0.001)
        initial_cash = engine.get_account().cash
        engine.place_order("000001", OrderSide.BUY, 1000, 10.0)

        # Cash should be reduced by cost + commission
        remaining = engine.get_account().cash
        assert remaining < initial_cash - 1000 * 10.0  # commission makes it less


class TestSignalsToOrders:
    def test_buy_signal(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        account = engine.get_account()
        suggestions = signals_to_orders(
            {"000001": 1},
            {"000001": 10.0},
            account,
        )
        assert len(suggestions) == 1
        assert suggestions[0]["side"] == "buy"
        assert suggestions[0]["quantity"] > 0

    def test_sell_signal(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        engine.place_order("000001", OrderSide.BUY, 1000, 10.0)
        account = engine.get_account()
        suggestions = signals_to_orders(
            {"000001": -1},
            {"000001": 11.0},
            account,
        )
        assert len(suggestions) == 1
        assert suggestions[0]["side"] == "sell"

    def test_hold_signal(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        account = engine.get_account()
        suggestions = signals_to_orders(
            {"000001": 0},
            {"000001": 10.0},
            account,
        )
        assert len(suggestions) == 0

    def test_no_duplicate_buy(self):
        engine = PaperTradeEngine(initial_capital=1_000_000)
        engine.place_order("000001", OrderSide.BUY, 1000, 10.0)
        account = engine.get_account()
        suggestions = signals_to_orders(
            {"000001": 1},  # buy signal but already holding
            {"000001": 10.0},
            account,
        )
        assert len(suggestions) == 0
