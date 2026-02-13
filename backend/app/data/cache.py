"""데이터 캐싱 레이어 (PostgreSQL MarketData 테이블 기반)"""

import uuid
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.data.provider import DataProvider, SymbolInfo
from app.db.models import MarketData, MarketType, TimeframeType
from app.utils.logger import logger


class CachedDataProvider(DataProvider):
    """DB 캐시를 앞에 두고, 미스 시 실제 프로바이더를 호출하는 래퍼"""

    def __init__(self, provider: DataProvider, db: Session):
        self._provider = provider
        self._db = db

    def _get_ttl(self, timeframe: TimeframeType) -> int:
        if timeframe == TimeframeType.D1:
            return settings.cache_ttl_daily
        return settings.cache_ttl_hourly

    async def fetch_ohlcv(
        self,
        symbol: str,
        market: MarketType,
        timeframe: TimeframeType,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        ttl = self._get_ttl(timeframe)
        cutoff = datetime.utcnow() - timedelta(seconds=ttl)

        # 캐시에서 유효한 데이터 조회
        cached = (
            self._db.query(MarketData)
            .filter(
                and_(
                    MarketData.symbol == symbol,
                    MarketData.market == market,
                    MarketData.timeframe == timeframe,
                    MarketData.timestamp >= start,
                    MarketData.timestamp <= end,
                    MarketData.fetched_at >= cutoff,
                )
            )
            .order_by(MarketData.timestamp)
            .all()
        )

        if cached:
            logger.info(
                "캐시 히트: %s %s %s (%d건)", symbol, market.value, timeframe.value, len(cached)
            )
            return self._rows_to_dataframe(cached)

        # 캐시 미스 → 실제 프로바이더 호출
        logger.info("캐시 미스: %s %s %s → API 호출", symbol, market.value, timeframe.value)
        df = await self._provider.fetch_ohlcv(symbol, market, timeframe, start, end)

        if not df.empty:
            self._upsert_cache(df, symbol, market, timeframe)

        return df

    def _upsert_cache(
        self,
        df: pd.DataFrame,
        symbol: str,
        market: MarketType,
        timeframe: TimeframeType,
    ) -> None:
        """DataFrame을 MarketData 테이블에 upsert"""
        now = datetime.utcnow()

        for _, row in df.iterrows():
            existing = (
                self._db.query(MarketData)
                .filter(
                    and_(
                        MarketData.symbol == symbol,
                        MarketData.market == market,
                        MarketData.timeframe == timeframe,
                        MarketData.timestamp == row["timestamp"],
                    )
                )
                .first()
            )

            if existing:
                existing.open = row["open"]
                existing.high = row["high"]
                existing.low = row["low"]
                existing.close = row["close"]
                existing.volume = int(row["volume"])
                existing.fetched_at = now
            else:
                record = MarketData(
                    id=str(uuid.uuid4()),
                    symbol=symbol,
                    market=market,
                    timeframe=timeframe,
                    timestamp=row["timestamp"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=int(row["volume"]),
                    fetched_at=now,
                )
                self._db.add(record)

        self._db.commit()
        logger.info("캐시 저장 완료: %s %d건", symbol, len(df))

    def _rows_to_dataframe(self, rows: List[MarketData]) -> pd.DataFrame:
        data = [
            {
                "timestamp": r.timestamp,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": int(r.volume),
            }
            for r in rows
        ]
        return pd.DataFrame(data)

    async def search_symbols(
        self,
        market: MarketType,
        query: str,
    ) -> List[SymbolInfo]:
        # 종목 검색은 캐시하지 않고 직접 호출
        return await self._provider.search_symbols(market, query)
