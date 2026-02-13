import pandas as pd
import pytest

from app.engine.order import OrderSide
from app.engine.portfolio import Portfolio
from app.engine.position import Position
from app.strategies.rsi import RSIStrategy


@pytest.fixture
def strategy():
    return RSIStrategy()


@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=100_000_000)


def make_bar(close: float, open_: float = 0, high: float = 0, low: float = 0, volume: int = 1000):
    return pd.Series({
        "open": open_ or close,
        "high": high or close,
        "low": low or close,
        "close": close,
        "volume": volume,
    })


def feed_prices(strategy, portfolio, symbol: str, prices: list):
    orders = []
    for price in prices:
        bars = {symbol: make_bar(price)}
        orders = strategy.on_bar(bars, portfolio)
    return orders


class TestRSIBuySignal:
    def test_buy_when_rsi_oversold(self, strategy, portfolio):
        # 연속 하락으로 RSI < 30 유도
        # 시작가에서 계속 하락
        prices = [10000 - i * 100 for i in range(20)]
        orders = feed_prices(strategy, portfolio, "005930", prices)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY
        assert orders[0].symbol == "005930"
        assert orders[0].weight == 0.3


class TestRSISellSignal:
    def test_sell_when_rsi_overbought(self, strategy, portfolio):
        # 포지션 보유 상태
        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10000, current_price=10000
        )
        # 연속 상승으로 RSI > 70 유도
        prices = [10000 + i * 100 for i in range(20)]
        orders = feed_prices(strategy, portfolio, "005930", prices)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL
        assert orders[0].symbol == "005930"


class TestRSILookbackInsufficient:
    def test_no_signal_before_required_bars(self, strategy, portfolio):
        # rsi_period=14, 최소 15개 필요. 14개만 feed
        for i in range(14):
            bars = {"005930": make_bar(10000 - i * 200)}
            orders = strategy.on_bar(bars, portfolio)
            assert len(orders) == 0


class TestRSINoSignal:
    def test_no_signal_in_neutral_zone(self, strategy, portfolio):
        # 가격이 등락을 반복하면 RSI가 30~70 사이에 머무름
        prices = []
        for i in range(30):
            if i % 2 == 0:
                prices.append(10000 + 50)
            else:
                prices.append(10000 - 50)
        orders = feed_prices(strategy, portfolio, "005930", prices)
        assert len(orders) == 0


class TestRSIDefaultParams:
    def test_defaults(self):
        s = RSIStrategy()
        assert s.parameters["rsi_period"] == 14
        assert s.parameters["oversold_threshold"] == 30
        assert s.parameters["overbought_threshold"] == 70
        assert s.parameters["position_weight"] == 0.3

    def test_custom_params(self):
        s = RSIStrategy({"rsi_period": 7, "oversold_threshold": 20})
        assert s.parameters["rsi_period"] == 7
        assert s.parameters["oversold_threshold"] == 20
