from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class PendingOrder:
    """
    전략이 생성하는 주문 요청.
    수량은 weight(비율)로 지정하며, 엔진이 다음 봉 시가 기준으로 실제 수량을 확정한다.
    """

    symbol: str
    side: OrderSide
    weight: float  # 포트폴리오 대비 투자 비율 (0.0 ~ 1.0)
    reason: Optional[str] = None


@dataclass
class FilledOrder:
    """체결 완료된 주문"""

    symbol: str
    side: OrderSide
    signal_price: float  # 시그널 발생 시점 가격 (봉 t의 종가)
    signal_date: datetime
    fill_price: float  # 실제 체결가 (봉 t+1의 시가 + 슬리피지)
    fill_date: datetime
    quantity: int
    commission: float
