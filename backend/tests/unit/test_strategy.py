import numpy as np
import pandas as pd
import pytest

from app.engine.order import OrderSide
from app.engine.portfolio import Portfolio
from app.engine.position import Position
from app.strategies.mean_reversion import MeanReversionStrategy


@pytest.fixture
def strategy():
    return MeanReversionStrategy()


@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=100_000_000)


def make_bar(close: float, open_: float = 0, high: float = 0, low: float = 0, volume: int = 1000):
    """OHLCV Series 생성 헬퍼"""
    return pd.Series({
        "open": open_ or close,
        "high": high or close,
        "low": low or close,
        "close": close,
        "volume": volume,
    })


def feed_prices(strategy, portfolio, symbol: str, prices: list):
    """여러 가격을 순차적으로 feed하고 마지막 봉의 orders를 반환"""
    orders = []
    for price in prices:
        bars = {symbol: make_bar(price)}
        orders = strategy.on_bar(bars, portfolio)
    return orders


class TestMeanReversionBuySignal:
    """가격이 평균 대비 2σ 이하일 때 매수 시그널 생성 검증"""

    def test_buy_signal_when_price_drops_below_threshold(self, strategy, portfolio):
        # lookback=20, 안정적인 가격 후 급락
        stable_prices = [72000.0] * 19
        # 급락: 평균 72000, std=0이면 안 되므로 약간의 변동 추가
        prices_with_variance = [72000 + (i % 3 - 1) * 100 for i in range(19)]
        # 마지막에 큰 하락
        mean = np.mean(prices_with_variance)
        std = np.std(prices_with_variance)
        # Z-Score < -2.0이 되려면: close < mean - 2*std
        drop_price = mean - 2.5 * std

        orders = feed_prices(strategy, portfolio, "005930", prices_with_variance + [drop_price])

        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY
        assert orders[0].symbol == "005930"
        assert orders[0].weight == 0.3


class TestMeanReversionSellSignal:
    """가격이 평균으로 회귀했을 때 매도 시그널 검증"""

    def test_sell_signal_when_price_reverts_to_mean(self, strategy, portfolio):
        # 먼저 매수 포지션을 만들어 놓는다
        portfolio.positions["005930"] = Position(
            symbol="005930",
            quantity=100,
            avg_price=70000,
            current_price=70000,
        )

        # lookback=20, 가격이 점차 상승하여 평균 회귀
        prices = [70000 + i * 100 for i in range(19)]
        # 마지막 가격: 평균 근처 (z-score > -0.5)
        mean = np.mean(prices)
        std = np.std(prices)
        # z_score > -exit_threshold(0.5)이면 매도
        # 평균 근처 또는 그 이상의 가격
        revert_price = mean + std  # z_score ≈ 1.0 > -0.5

        orders = feed_prices(strategy, portfolio, "005930", prices + [revert_price])

        assert len(orders) == 1
        assert orders[0].side == OrderSide.SELL
        assert orders[0].symbol == "005930"
        assert orders[0].weight == 1.0


class TestLookbackInsufficient:
    """lookback 기간 미달 시 시그널 없음 검증"""

    def test_no_signal_before_lookback_period(self, strategy, portfolio):
        # 19개 봉만 feed (lookback=20 미달)
        for i in range(19):
            bars = {"005930": make_bar(72000 + i * 100)}
            orders = strategy.on_bar(bars, portfolio)
            assert len(orders) == 0

    def test_signal_possible_at_lookback_period(self, strategy, portfolio):
        # 20개 봉이면 시그널 가능 (조건 충족 시)
        prices = [72000 + (i % 3 - 1) * 100 for i in range(19)]
        mean = np.mean(prices)
        std = np.std(prices)
        drop_price = mean - 3 * std  # 확실한 매수 시그널

        orders = feed_prices(strategy, portfolio, "005930", prices + [drop_price])
        assert len(orders) == 1


class TestZeroStdDev:
    """표준편차 0일 때 시그널 없음 검증"""

    def test_no_signal_when_std_is_zero(self, strategy, portfolio):
        # 모든 가격이 동일 → std=0
        same_prices = [72000.0] * 20
        orders = feed_prices(strategy, portfolio, "005930", same_prices)
        assert len(orders) == 0

    def test_no_signal_when_std_is_zero_with_position(self, strategy, portfolio):
        portfolio.positions["005930"] = Position(
            symbol="005930",
            quantity=100,
            avg_price=72000,
            current_price=72000,
        )
        same_prices = [72000.0] * 20
        orders = feed_prices(strategy, portfolio, "005930", same_prices)
        assert len(orders) == 0


class TestMultiSymbolIndependentState:
    """다중 종목에서 종목별 독립 상태 유지 검증"""

    def test_independent_state_per_symbol(self, strategy, portfolio):
        # 종목 A: 19봉 feed
        for i in range(19):
            bars = {"A": make_bar(72000 + i * 100)}
            strategy.on_bar(bars, portfolio)

        # 종목 B: 별도로 19봉 feed
        for i in range(19):
            bars = {"B": make_bar(50000 + i * 50)}
            strategy.on_bar(bars, portfolio)

        # 각 종목의 state가 독립적인지 확인
        state_a = strategy._get_state("A")
        state_b = strategy._get_state("B")

        assert len(state_a["price_history"]) == 19
        assert len(state_b["price_history"]) == 19
        assert state_a["price_history"][0] == 72000
        assert state_b["price_history"][0] == 50000

    def test_simultaneous_bars_for_multiple_symbols(self, strategy, portfolio):
        # 두 종목을 동시에 bars로 전달
        prices_a = [72000 + (i % 3 - 1) * 100 for i in range(19)]
        prices_b = [50000 + (i % 3 - 1) * 50 for i in range(19)]

        for i in range(19):
            bars = {
                "A": make_bar(prices_a[i]),
                "B": make_bar(prices_b[i]),
            }
            strategy.on_bar(bars, portfolio)

        # A만 급락 시그널
        mean_a = np.mean(prices_a)
        std_a = np.std(prices_a)
        drop_a = mean_a - 3 * std_a

        mean_b = np.mean(prices_b)  # B는 정상 범위
        normal_b = mean_b

        bars = {
            "A": make_bar(drop_a),
            "B": make_bar(normal_b),
        }
        orders = strategy.on_bar(bars, portfolio)

        # A만 매수 시그널, B는 없음
        assert len(orders) == 1
        assert orders[0].symbol == "A"
        assert orders[0].side == OrderSide.BUY


class TestCustomParameters:
    """커스텀 파라미터 동작 검증"""

    def test_custom_entry_threshold(self, portfolio):
        # 더 낮은 entry_threshold로 더 쉽게 매수 시그널 발생
        strategy = MeanReversionStrategy({"entry_threshold": 1.0})
        prices = [72000 + (i % 3 - 1) * 100 for i in range(19)]
        mean = np.mean(prices)
        std = np.std(prices)
        # entry_threshold=1.0이면 z < -1.0에서 매수
        drop_price = mean - 1.5 * std

        orders = feed_prices(strategy, portfolio, "005930", prices + [drop_price])
        assert len(orders) == 1
        assert orders[0].side == OrderSide.BUY

    def test_custom_position_weight(self, portfolio):
        strategy = MeanReversionStrategy({"position_weight": 0.5})
        prices = [72000 + (i % 3 - 1) * 100 for i in range(19)]
        mean = np.mean(prices)
        std = np.std(prices)
        drop_price = mean - 3 * std

        orders = feed_prices(strategy, portfolio, "005930", prices + [drop_price])
        assert len(orders) == 1
        assert orders[0].weight == 0.5

    def test_default_parameters(self):
        strategy = MeanReversionStrategy()
        assert strategy.parameters["lookback_period"] == 20
        assert strategy.parameters["entry_threshold"] == 2.0
        assert strategy.parameters["exit_threshold"] == 0.5
        assert strategy.parameters["position_weight"] == 0.3


class TestSampleOHLCV:
    """sample_ohlcv.csv로 전략 동작 확인"""

    def test_strategy_runs_with_csv_data(self, strategy, portfolio):
        import os

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "sample_ohlcv.csv"
        )
        df = pd.read_csv(csv_path)

        all_orders = []
        for _, row in df.iterrows():
            bars = {"005930": row}
            orders = strategy.on_bar(bars, portfolio)
            all_orders.extend(orders)

        # CSV 데이터로 전략이 에러 없이 실행되는지 확인
        assert isinstance(all_orders, list)
