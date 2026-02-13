import pandas as pd
import pytest

from app.engine.order import OrderSide
from app.engine.portfolio import Portfolio
from app.engine.position import Position
from app.strategies.bollinger_bands import BollingerBandsStrategy


@pytest.fixture
def strategy():
    return BollingerBandsStrategy()


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


class TestBollingerBuySignal:
    def test_buy_when_price_below_lower_band(self, strategy, portfolio):
        # 안정적 가격 후 급락 → 하단 밴드 이하
        prices = [10000 + (i % 5 - 2) * 50 for i in range(19)]
        # 큰 하락으로 하단 밴드 돌파
        drop_price = 9000
        orders = feed_prices(strategy, portfolio, "005930", prices + [drop_price])

        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY
        assert orders[0].symbol == "005930"
        assert orders[0].weight == 0.3


class TestBollingerSellSignal:
    def test_sell_when_price_above_upper_band(self, strategy, portfolio):
        # 포지션 보유 상태
        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10000, current_price=10000
        )
        prices = [10000 + (i % 5 - 2) * 50 for i in range(19)]
        # 큰 상승으로 상단 밴드 돌파
        spike_price = 11500
        orders = feed_prices(strategy, portfolio, "005930", prices + [spike_price])

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL
        assert orders[0].symbol == "005930"


class TestBollingerLookbackInsufficient:
    def test_no_signal_before_lookback(self, strategy, portfolio):
        # bb_period=20, 19개만 feed
        for i in range(19):
            bars = {"005930": make_bar(10000 + i * 10)}
            orders = strategy.on_bar(bars, portfolio)
            assert len(orders) == 0


class TestBollingerNoSignal:
    def test_no_signal_within_bands(self, strategy, portfolio):
        # 가격이 밴드 범위 내에 머무르면 시그널 없음
        prices = [10000 + (i % 3 - 1) * 10 for i in range(25)]
        orders = feed_prices(strategy, portfolio, "005930", prices)
        assert len(orders) == 0


class TestBollingerDefaultParams:
    def test_defaults(self):
        s = BollingerBandsStrategy()
        assert s.parameters["bb_period"] == 20
        assert s.parameters["bb_std"] == 2.0
        assert s.parameters["position_weight"] == 0.3

    def test_custom_params(self):
        s = BollingerBandsStrategy({"bb_period": 10, "bb_std": 1.5})
        assert s.parameters["bb_period"] == 10
        assert s.parameters["bb_std"] == 1.5
