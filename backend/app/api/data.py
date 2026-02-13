"""데이터 API 엔드포인트"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.data.cache import CachedDataProvider
from app.data.kis_api import KISDataProvider
from app.db.models import MarketType, TimeframeType
from app.db.session import get_db
from app.utils.response import success_response

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/symbols")
def search_symbols(
    market: MarketType = Query(...),
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """종목 검색"""
    kis_client = KISDataProvider()
    cached = CachedDataProvider(kis_client, db)

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(cached.search_symbols(market, query))
    finally:
        loop.close()

    items = [
        {
            "symbol": s.symbol,
            "name": s.name,
            "market": s.market.value,
            "sector": s.sector,
            "industry": s.industry,
        }
        for s in results
    ]
    return success_response(data=items)


@router.get("/ohlcv")
def get_ohlcv(
    symbol: str = Query(...),
    market: MarketType = Query(...),
    timeframe: TimeframeType = Query(TimeframeType.D1),
    start: datetime = Query(..., alias="from"),
    end: datetime = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    """과거 시세 조회"""
    kis_client = KISDataProvider()
    cached = CachedDataProvider(kis_client, db)

    loop = asyncio.new_event_loop()
    try:
        df = loop.run_until_complete(
            cached.fetch_ohlcv(symbol, market, timeframe, start, end)
        )
    finally:
        loop.close()

    if df.empty:
        return success_response(data=[])

    records = df.to_dict(orient="records")
    # datetime → ISO string 변환
    for r in records:
        for key in ("timestamp",):
            if key in r and hasattr(r[key], "isoformat"):
                r[key] = r[key].isoformat()

    return success_response(data=records)
