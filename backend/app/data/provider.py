"""데이터 프로바이더 인터페이스 (ABC)"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pandas as pd

from app.db.models import MarketType, TimeframeType


@dataclass
class SymbolInfo:
    """종목 정보"""

    symbol: str
    name: str
    market: MarketType
    sector: Optional[str] = None
    industry: Optional[str] = None


class DataProvider(ABC):
    """데이터 프로바이더 추상 클래스"""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        market: MarketType,
        timeframe: TimeframeType,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """OHLCV 데이터를 조회한다.

        Returns:
            columns: [timestamp, open, high, low, close, volume]
            index: RangeIndex
        """
        ...

    @abstractmethod
    async def search_symbols(
        self,
        market: MarketType,
        query: str,
    ) -> List[SymbolInfo]:
        """종목을 검색한다."""
        ...
