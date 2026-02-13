from typing import Dict, Optional

from app.engine.position import Position


class Portfolio:
    """포트폴리오 관리"""

    def __init__(self, initial_capital: float):
        self.cash: float = initial_capital
        self.positions: Dict[str, Position] = {}

    @property
    def equity(self) -> float:
        """총 평가액 = 현금 + 모든 포지션 시가평가"""
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash + position_value

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def get_position_weight(self, symbol: str) -> float:
        """해당 종목이 포트폴리오에서 차지하는 비율"""
        pos = self.positions.get(symbol)
        if pos is None or self.equity == 0:
            return 0.0
        return pos.market_value / self.equity

    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """시가평가 갱신"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price

    def execute_buy(
        self, symbol: str, quantity: int, fill_price: float, commission: float
    ) -> None:
        """매수 체결"""
        total_cost = fill_price * quantity + commission
        if total_cost > self.cash:
            raise ValueError(f"현금 부족: 필요 {total_cost:.2f}, 보유 {self.cash:.2f}")

        self.cash -= total_cost

        if symbol in self.positions:
            self.positions[symbol].add(quantity, fill_price)
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=fill_price,
                current_price=fill_price,
            )

    def execute_sell(
        self, symbol: str, quantity: int, fill_price: float, commission: float
    ) -> None:
        """매도 체결"""
        pos = self.positions.get(symbol)
        if pos is None:
            raise ValueError(f"보유하지 않은 종목: {symbol}")

        pos.reduce(quantity)
        self.cash += fill_price * quantity - commission

        # 포지션 완전 청산 시 제거
        if pos.is_closed:
            del self.positions[symbol]
        else:
            pos.current_price = fill_price
