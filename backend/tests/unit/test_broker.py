import pytest

from app.db.models import TimeframeType
from app.engine.broker import Broker


class TestBrokerCommission:
    """수수료 계산 테스트"""

    def test_kr_commission(self):
        """KR 시장 수수료: 0.015%"""
        broker = Broker("KR", TimeframeType.D1)
        # 70,000원 × 100주 = 7,000,000원 → 수수료 = 7,000,000 × 0.00015 = 1,050
        commission = broker.calculate_commission(70_000, 100)
        assert commission == pytest.approx(1_050.0)

    def test_kr_no_min_commission(self):
        """KR 시장은 최소 수수료 없음 (0원)"""
        broker = Broker("KR", TimeframeType.D1)
        # 소액 거래도 최소 수수료 적용 안됨
        commission = broker.calculate_commission(1_000, 1)
        assert commission == pytest.approx(0.15)

    def test_us_commission(self):
        """US 시장 수수료: 0.25%"""
        broker = Broker("US", TimeframeType.D1)
        # $150 × 50주 = $7,500 → 수수료 = 7,500 × 0.0025 = $18.75
        commission = broker.calculate_commission(150.0, 50)
        assert commission == pytest.approx(18.75)

    def test_us_min_commission_applied(self):
        """US 시장 최소 수수료 $1 적용 케이스"""
        broker = Broker("US", TimeframeType.D1)
        # $10 × 1주 = $10 → raw = 10 × 0.0025 = $0.025 → min $1 적용
        commission = broker.calculate_commission(10.0, 1)
        assert commission == 1.0

    def test_us_min_commission_not_applied(self):
        """US 시장 수수료가 $1 초과하면 min_commission 미적용"""
        broker = Broker("US", TimeframeType.D1)
        # $200 × 10주 = $2,000 → raw = 2,000 × 0.0025 = $5.0 > $1
        commission = broker.calculate_commission(200.0, 10)
        assert commission == pytest.approx(5.0)


class TestBrokerSlippage:
    """슬리피지 및 체결가 테스트"""

    def test_daily_slippage(self):
        """일봉 슬리피지 적용"""
        broker = Broker("KR", TimeframeType.D1)
        assert broker.get_slippage() == 0.001

    def test_hourly_slippage(self):
        """시간봉 슬리피지 적용"""
        broker = Broker("KR", TimeframeType.H1)
        assert broker.get_slippage() == 0.0005

    def test_buy_fill_price(self):
        """매수: 시가보다 높게(불리하게) 체결"""
        broker = Broker("KR", TimeframeType.D1)
        fill = broker.calculate_fill_price(70_000, "BUY")
        # 70,000 × (1 + 0.001) = 70,070
        assert fill == pytest.approx(70_070.0)

    def test_sell_fill_price(self):
        """매도: 시가보다 낮게(불리하게) 체결"""
        broker = Broker("KR", TimeframeType.D1)
        fill = broker.calculate_fill_price(70_000, "SELL")
        # 70,000 × (1 - 0.001) = 69,930
        assert fill == pytest.approx(69_930.0)


class TestBrokerQuantity:
    """수량 계산 + 포지션 한도 테스트"""

    def test_basic_quantity(self):
        """기본 수량 계산 (정수 버림)"""
        broker = Broker("KR", TimeframeType.D1)
        # equity=10,000,000, weight=0.2 → target=2,000,000
        # fill_price=70,070 → 2,000,000 / 70,070 = 28.55 → 28주
        qty = broker.calculate_quantity(10_000_000, 0.2, 70_070)
        assert qty == 28

    def test_position_weight_limit(self):
        """종목당 최대 40% 초과 시 수량 축소"""
        broker = Broker("KR", TimeframeType.D1)
        # equity=10,000,000, weight=0.5 → target=5,000,000
        # MAX_POSITION_WEIGHT=0.4 → max=4,000,000
        # current_position_value=3,000,000 → allowed=1,000,000
        # 1,000,000 / 70,000 = 14.28 → 14주
        qty = broker.calculate_quantity(10_000_000, 0.5, 70_000, 3_000_000)
        assert qty == 14

    def test_below_min_order_returns_zero(self):
        """최소 주문 금액 미달 시 0 반환"""
        broker = Broker("KR", TimeframeType.D1)
        # equity=10,000,000, weight=0.005 → target=50,000 < min_order(100,000)
        qty = broker.calculate_quantity(10_000_000, 0.005, 70_000)
        assert qty == 0

    def test_us_min_order(self):
        """US 시장 최소 주문 금액 $100"""
        broker = Broker("US", TimeframeType.D1)
        # equity=10,000, weight=0.005 → target=50 < min_order(100)
        qty = broker.calculate_quantity(10_000, 0.005, 150.0)
        assert qty == 0


class TestBrokerValidation:
    """주문 검증 테스트"""

    def test_valid_order(self):
        """정상 주문"""
        broker = Broker("KR", TimeframeType.D1)
        # equity=10,000,000, cash=10,000,000
        # 70,000 × 10 = 700,000 + commission(1,050) = 701,050
        # remaining = 10,000,000 - 701,050 = 9,298,950 > 500,000 (5%)
        valid, reason = broker.validate_order(10_000_000, 10_000_000, 70_000, 10)
        assert valid is True
        assert reason is None

    def test_insufficient_cash(self):
        """현금 부족 시 주문 거부"""
        broker = Broker("KR", TimeframeType.D1)
        # cash=500,000, 70,000 × 10 = 700,000 > 500,000
        valid, reason = broker.validate_order(10_000_000, 500_000, 70_000, 10)
        assert valid is False
        assert reason == "INSUFFICIENT_CASH"

    def test_cash_reserve_violation(self):
        """최소 잔여 현금 5% 미달 시 거부"""
        broker = Broker("KR", TimeframeType.D1)
        # equity=10,000,000 → reserve=500,000
        # cash=1,200,000, 70,000 × 10 = 700,000 + commission(1,050) = 701,050
        # remaining = 1,200,000 - 701,050 = 498,950 < 500,000
        valid, reason = broker.validate_order(10_000_000, 1_200_000, 70_000, 10)
        assert valid is False
        assert reason == "CASH_RESERVE_VIOLATION"

    def test_below_min_order_amount(self):
        """최소 주문 금액 미달 시 거부"""
        broker = Broker("KR", TimeframeType.D1)
        # 70,000 × 1 = 70,000 < min_order(100,000)
        valid, reason = broker.validate_order(10_000_000, 10_000_000, 70_000, 1)
        assert valid is False
        assert reason == "BELOW_MIN_ORDER"
