from dataclasses import dataclass, field


@dataclass
class Position:
    """개별 종목 포지션"""

    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        """현재가 기준 시가평가액"""
        return self.quantity * self.current_price

    def add(self, quantity: int, price: float) -> None:
        """매수 시 평균단가 재계산"""
        if quantity <= 0:
            raise ValueError("매수 수량은 0보다 커야 합니다.")
        total_cost = self.avg_price * self.quantity + price * quantity
        self.quantity += quantity
        self.avg_price = total_cost / self.quantity
        self.current_price = price

    def reduce(self, quantity: int) -> None:
        """매도 시 수량 차감 (평균단가 유지)"""
        if quantity <= 0:
            raise ValueError("매도 수량은 0보다 커야 합니다.")
        if quantity > self.quantity:
            raise ValueError(
                f"보유 수량({self.quantity})보다 많은 수량({quantity})을 매도할 수 없습니다."
            )
        self.quantity -= quantity

    @property
    def is_closed(self) -> bool:
        return self.quantity == 0
