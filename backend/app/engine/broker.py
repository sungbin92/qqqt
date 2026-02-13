import math
from typing import Optional, Tuple

from app.config import MARKET_CONFIGS, MarketConfig
from app.db.models import TimeframeType


class Broker:
    """
    주문 체결 처리.
    MarketConfig 기반으로 수수료/슬리피지를 계산하고,
    포지션 한도를 엔진 레벨에서 강제한다.
    """

    # 포지션 한도 기본값 (config로 오버라이드 가능)
    MAX_POSITION_WEIGHT = 0.40  # 종목당 최대 40%
    MIN_CASH_RESERVE_RATIO = 0.05  # 최소 잔여 현금 5%

    def __init__(self, market: str, timeframe: TimeframeType):
        self.config: MarketConfig = MARKET_CONFIGS[market]
        self.timeframe = timeframe

    def get_slippage(self) -> float:
        if self.timeframe == TimeframeType.D1:
            return self.config.slippage_daily
        return self.config.slippage_hourly

    def calculate_fill_price(self, next_open: float, side: str) -> float:
        """다음 봉 시가 + 슬리피지로 체결가 결정"""
        slippage = self.get_slippage()
        if side == "BUY":
            return next_open * (1 + slippage)  # 매수: 불리하게
        return next_open * (1 - slippage)  # 매도: 불리하게

    def calculate_commission(self, fill_price: float, quantity: int) -> float:
        """수수료 계산"""
        raw = fill_price * quantity * self.config.commission_rate
        return max(raw, self.config.min_commission)

    def calculate_quantity(
        self,
        portfolio_equity: float,
        weight: float,
        fill_price: float,
        current_position_value: float = 0,
    ) -> int:
        """
        투자 비율(weight)과 체결가로 실제 수량 확정.
        포지션 한도를 적용하여 수량을 축소할 수 있다.
        """
        target_value = portfolio_equity * weight

        # 1) 종목당 최대 비중 검증
        max_value = portfolio_equity * self.MAX_POSITION_WEIGHT
        allowed_value = max_value - current_position_value
        target_value = min(target_value, allowed_value)

        # 2) 최소 주문 금액 검증
        if target_value < self.config.min_order_amount:
            return 0

        # 3) 정수 수량 (소수점 버림)
        quantity = math.floor(target_value / fill_price)
        return max(quantity, 0)

    def validate_order(
        self,
        portfolio_equity: float,
        available_cash: float,
        fill_price: float,
        quantity: int,
    ) -> Tuple[bool, Optional[str]]:
        """주문 최종 검증"""
        order_value = fill_price * quantity
        commission = self.calculate_commission(fill_price, quantity)
        total_cost = order_value + commission

        # 현금 부족
        if total_cost > available_cash:
            return False, "INSUFFICIENT_CASH"

        # 최소 잔여 현금 확보
        remaining = available_cash - total_cost
        if remaining < portfolio_equity * self.MIN_CASH_RESERVE_RATIO:
            return False, "CASH_RESERVE_VIOLATION"

        # 최소 주문 금액
        if order_value < self.config.min_order_amount:
            return False, "BELOW_MIN_ORDER"

        return True, None
