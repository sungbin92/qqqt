from abc import ABC, abstractmethod
from typing import Any, Dict, List

import pandas as pd

from app.engine.order import PendingOrder


class Strategy(ABC):
    """
    전략 베이스 클래스.

    - 다중 종목 지원: bars가 Dict[symbol, pd.Series]로 전달
    - 종목별 상태는 self._state[symbol]에 저장
    """

    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name = self.__class__.__name__
        self._state: Dict[str, Dict[str, Any]] = {}

    def _get_state(self, symbol: str) -> Dict[str, Any]:
        if symbol not in self._state:
            self._state[symbol] = self._init_state()
        return self._state[symbol]

    def _init_state(self) -> Dict[str, Any]:
        return {"price_history": [], "volume_history": []}

    @abstractmethod
    def on_bar(
        self,
        bars: Dict[str, pd.Series],
        portfolio: "Portfolio",
    ) -> List[PendingOrder]:
        """
        새 봉 도착 시 호출.

        Args:
            bars: 현재 시점의 각 종목 OHLCV 데이터
            portfolio: 현재 포트폴리오 상태 (읽기 전용)

        Returns:
            실행할 PendingOrder 리스트.
        """
        pass
