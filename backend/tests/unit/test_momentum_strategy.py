import pandas as pd
import pytest

from app.engine.order import OrderSide
from app.engine.portfolio import Portfolio
from app.engine.position import Position
from app.strategies.momentum_breakout import MomentumBreakoutStrategy


@pytest.fixture
def strategy():
    return MomentumBreakoutStrategy()


@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=100_000_000)


def make_bar(close: float, volume: int = 1000, open_: float = 0, high: float = 0, low: float = 0):
    return pd.Series({
        "open": open_ or close,
        "high": high or close,
        "low": low or close,
        "close": close,
        "volume": volume,
    })


def feed_bars(strategy, portfolio, symbol: str, prices: list, volumes: list):
    """여러 봉을 순차적으로 feed하고 마지막 봉의 orders를 반환"""
    orders = []
    for price, vol in zip(prices, volumes):
        bars = {symbol: make_bar(price, volume=vol)}
        orders = strategy.on_bar(bars, portfolio)
    return orders


class TestMomentumBreakoutBuySignal:
    """이동평균 돌파 + 거래량 급증 시 매수 시그널 검증"""

    def test_buy_signal_on_breakout_with_volume(self, strategy, portfolio):
        # 19봉: MA 아래에서 안정, 거래량 보통
        prices = [10000.0] * 19
        volumes = [1000] * 19
        # 20번째 봉: 가격 돌파 + 거래량 2배 이상
        prices.append(10500.0)  # MA=10000 근처, 10500 > MA
        volumes.append(2500)  # 2.5x > 2.0 threshold

        orders = feed_bars(strategy, portfolio, "005930", prices, volumes)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY
        assert orders[0].symbol == "005930"
        assert orders[0].weight == 0.3


class TestMomentumBreakoutStopLoss:
    """손절 조건 (-5%) 시 매도 시그널 검증"""

    def test_sell_signal_on_stop_loss(self, strategy, portfolio):
        # 먼저 매수 시그널 발생시켜 entry_price 기록
        prices = [10000.0] * 19 + [10500.0]
        volumes = [1000] * 19 + [2500]
        feed_bars(strategy, portfolio, "005930", prices, volumes)

        # 포지션 수동 설정 (엔진이 하는 역할)
        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10500, current_price=10500
        )

        # 5% 이상 하락: 10500 * 0.95 = 9975 → 9900이면 -5.7%
        bars = {"005930": make_bar(9900.0, volume=1000)}
        orders = strategy.on_bar(bars, portfolio)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL
        assert orders[0].weight == 1.0
        assert "손절" in orders[0].reason


class TestMomentumBreakoutTakeProfit:
    """익절 조건 (+15%) 시 매도 시그널 검증"""

    def test_sell_signal_on_take_profit(self, strategy, portfolio):
        # 매수 시그널로 entry_price 기록
        prices = [10000.0] * 19 + [10500.0]
        volumes = [1000] * 19 + [2500]
        feed_bars(strategy, portfolio, "005930", prices, volumes)

        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10500, current_price=10500
        )

        # 15% 이상 상승: 10500 * 1.15 = 12075 → 12100이면 +15.2%
        bars = {"005930": make_bar(12100.0, volume=1000)}
        orders = strategy.on_bar(bars, portfolio)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL
        assert orders[0].weight == 1.0
        assert "익절" in orders[0].reason


class TestVolumeConditionNotMet:
    """거래량 조건 미달 시 매수 안 함 검증"""

    def test_no_buy_when_volume_insufficient(self, strategy, portfolio):
        # 가격은 돌파하지만 거래량이 부족
        prices = [10000.0] * 19 + [10500.0]
        volumes = [1000] * 19 + [1500]  # 1.5x < 2.0 threshold

        orders = feed_bars(strategy, portfolio, "005930", prices, volumes)

        assert len(orders) == 0

    def test_no_buy_when_price_below_ma(self, strategy, portfolio):
        # 거래량은 충분하지만 가격이 MA 이하
        prices = [10000.0] * 19 + [9500.0]
        volumes = [1000] * 19 + [2500]

        orders = feed_bars(strategy, portfolio, "005930", prices, volumes)

        assert len(orders) == 0


class TestMomentumMultiSymbol:
    """다중 종목 독립 상태 검증"""

    def test_independent_state_per_symbol(self, strategy, portfolio):
        # 종목 A: 매수 조건 충족
        # 종목 B: 거래량 미달
        prices_a = [10000.0] * 19
        prices_b = [50000.0] * 19
        volumes = [1000] * 19

        for i in range(19):
            bars = {
                "A": make_bar(prices_a[i], volume=volumes[i]),
                "B": make_bar(prices_b[i], volume=volumes[i]),
            }
            strategy.on_bar(bars, portfolio)

        # A: 돌파 + 거래량 급증 / B: 돌파하지만 거래량 부족
        bars = {
            "A": make_bar(10500.0, volume=2500),
            "B": make_bar(51000.0, volume=1500),
        }
        orders = strategy.on_bar(bars, portfolio)

        assert len(orders) == 1
        assert orders[0].symbol == "A"
        assert orders[0].side == OrderSide.BUY


class TestMomentumCustomParameters:
    """커스텀 파라미터 동작 검증"""

    def test_custom_stop_loss(self, portfolio):
        strategy = MomentumBreakoutStrategy({"stop_loss_pct": 0.03})

        # 매수 시그널
        prices = [10000.0] * 19 + [10500.0]
        volumes = [1000] * 19 + [2500]
        feed_bars(strategy, portfolio, "005930", prices, volumes)

        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10500, current_price=10500
        )

        # 3% 하락: 10500 * 0.97 = 10185 → 10100이면 -3.8%
        bars = {"005930": make_bar(10100.0, volume=1000)}
        orders = strategy.on_bar(bars, portfolio)

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL

    def test_default_parameters(self):
        strategy = MomentumBreakoutStrategy()
        assert strategy.parameters["ma_period"] == 20
        assert strategy.parameters["volume_ma_period"] == 20
        assert strategy.parameters["volume_threshold"] == 2.0
        assert strategy.parameters["stop_loss_pct"] == 0.05
        assert strategy.parameters["take_profit_pct"] == 0.15
        assert strategy.parameters["position_weight"] == 0.3


class TestLookbackInsufficient:
    """MA 기간 미달 시 시그널 없음"""

    def test_no_signal_before_ma_period(self, strategy, portfolio):
        for i in range(19):
            bars = {"005930": make_bar(10000.0 + i * 100, volume=3000)}
            orders = strategy.on_bar(bars, portfolio)
            assert len(orders) == 0


class TestNoDoubleEntry:
    """포지션 보유 중 추가 매수 안 함"""

    def test_no_buy_when_already_holding(self, strategy, portfolio):
        # 첫 매수 시그널
        prices = [10000.0] * 19 + [10500.0]
        volumes = [1000] * 19 + [2500]
        feed_bars(strategy, portfolio, "005930", prices, volumes)

        # 포지션 보유 상태
        portfolio.positions["005930"] = Position(
            symbol="005930", quantity=100, avg_price=10500, current_price=10500
        )

        # 또다시 돌파 + 거래량 조건 충족해도 매수 안 함
        bars = {"005930": make_bar(11000.0, volume=3000)}
        orders = strategy.on_bar(bars, portfolio)

        # 손절/익절 조건 미충족이면 주문 없음
        # 11000 vs entry 10500: +4.8% (익절 15% 미달, 손절 5% 미달)
        assert len(orders) == 0
