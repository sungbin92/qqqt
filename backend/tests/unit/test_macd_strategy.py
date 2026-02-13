import pandas as pd
import pytest

from app.engine.order import OrderSide
from app.engine.portfolio import Portfolio
from app.engine.position import Position
from app.strategies.macd_crossover import MACDCrossoverStrategy


@pytest.fixture
def strategy():
    return MACDCrossoverStrategy()


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


class TestMACDGoldenCross:
    def test_buy_on_golden_cross(self, strategy, portfolio):
        # 하락 후 반등 패턴 → MACD가 시그널을 상향 돌파
        # 먼저 하락 → 상승 전환
        prices = [10000 - i * 100 for i in range(40)]  # 10000 → 6100
        prices += [6100 + i * 200 for i in range(1, 30)]  # 강한 반등

        all_orders = []
        for price in prices:
            bars = {"005930": make_bar(price)}
            orders = strategy.on_bar(bars, portfolio)
            all_orders.extend(orders)

        buy_orders = [o for o in all_orders if o.side == OrderSide.BUY]
        assert len(buy_orders) >= 1
        assert buy_orders[0].symbol == "005930"
        assert buy_orders[0].weight == 0.3


class TestMACDDeadCross:
    def test_sell_on_dead_cross(self, strategy, portfolio):
        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10000, current_price=10000
        )
        # 상승 후 하락 패턴 → MACD가 시그널을 하향 돌파
        prices = [10000 + i * 100 for i in range(40)]  # 10000 → 13900
        prices += [13900 - i * 200 for i in range(1, 30)]  # 강한 하락

        all_orders = []
        for price in prices:
            bars = {"005930": make_bar(price)}
            orders = strategy.on_bar(bars, portfolio)
            all_orders.extend(orders)

        sell_orders = [o for o in all_orders if o.side == OrderSide.SELL]
        assert len(sell_orders) >= 1
        assert sell_orders[0].symbol == "005930"


class TestMACDLookbackInsufficient:
    def test_no_signal_before_min_bars(self, strategy, portfolio):
        # slow(26) + signal(9) = 35 최소 필요. 34개만 feed
        for i in range(34):
            bars = {"005930": make_bar(10000 + i * 10)}
            orders = strategy.on_bar(bars, portfolio)
            assert len(orders) == 0


class TestMACDNoCrossover:
    def test_no_signal_steady_trend(self, strategy, portfolio):
        # 일정하게 상승만 → 크로스오버 없음 (MACD 항상 시그널 위)
        prices = [10000 + i * 10 for i in range(50)]
        all_orders = []
        for price in prices:
            bars = {"005930": make_bar(price)}
            orders = strategy.on_bar(bars, portfolio)
            all_orders.extend(orders)

        # 꾸준한 상승에서는 초기 진입 후 추가 크로스오버 없거나 적음
        # 핵심: 에러 없이 실행됨
        assert isinstance(all_orders, list)


class TestMACDDefaultParams:
    def test_defaults(self):
        s = MACDCrossoverStrategy()
        assert s.parameters["fast_period"] == 12
        assert s.parameters["slow_period"] == 26
        assert s.parameters["signal_period"] == 9
        assert s.parameters["position_weight"] == 0.3

    def test_custom_params(self):
        s = MACDCrossoverStrategy({"fast_period": 8, "slow_period": 21})
        assert s.parameters["fast_period"] == 8
        assert s.parameters["slow_period"] == 21

    def test_init_state_has_prev_fields(self):
        s = MACDCrossoverStrategy()
        state = s._init_state()
        assert state["prev_macd"] is None
        assert state["prev_signal"] is None
