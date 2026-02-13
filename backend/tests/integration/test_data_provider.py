"""데이터 프로바이더 통합 테스트 (respx Mock 기반)"""

import uuid
from datetime import datetime, timedelta

import pandas as pd
import pytest
import respx
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data.cache import CachedDataProvider
from app.data.kis_api import (
    KIS_BASE_URL,
    KR_DAILY_PRICE_URL,
    KR_TIME_PRICE_URL,
    TOKEN_URL,
    US_DAILY_PRICE_URL,
    US_TIME_PRICE_URL,
    US_SEARCH_URL,
    KISDataProvider,
)
from app.data.provider import DataProvider, SymbolInfo
from app.db.models import Base, MarketData, MarketType, TimeframeType


# ── Fixtures ──


@pytest.fixture
def kis_provider():
    """테스트용 KIS 프로바이더 (Mock URL 사용)"""
    provider = KISDataProvider(
        app_key="test_key",
        app_secret="test_secret",
        base_url=KIS_BASE_URL,
    )
    return provider


@pytest.fixture
def db_session():
    """인메모리 SQLite 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _token_response():
    return Response(
        200,
        json={
            "access_token": "mock_token_12345",
            "token_type": "Bearer",
            "expires_in": 86400,
        },
    )


def _daily_ohlcv_response(dates_prices):
    """dates_prices: list of (date_str_YYYYMMDD, open, high, low, close, volume)"""
    output2 = []
    for d, o, h, l, c, v in dates_prices:
        output2.append(
            {
                "stck_bsop_date": d,
                "stck_oprc": str(o),
                "stck_hgpr": str(h),
                "stck_lwpr": str(l),
                "stck_clpr": str(c),
                "acml_vol": str(v),
            }
        )
    return Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": output2})


def _hourly_ohlcv_response(items):
    """items: list of (date_str, time_str_HHMMSS, open, high, low, close, volume)"""
    output2 = []
    for d, t, o, h, l, c, v in items:
        output2.append(
            {
                "stck_bsop_date": d,
                "stck_cntg_hour": t,
                "stck_oprc": str(o),
                "stck_hgpr": str(h),
                "stck_lwpr": str(l),
                "stck_prpr": str(c),
                "cntg_vol": str(v),
            }
        )
    return Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": output2})


# ── DataProvider ABC 테스트 ──


class TestDataProviderInterface:
    def test_symbol_info_creation(self):
        info = SymbolInfo(symbol="005930", name="삼성전자", market=MarketType.KR)
        assert info.symbol == "005930"
        assert info.name == "삼성전자"
        assert info.market == MarketType.KR
        assert info.sector is None

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataProvider()


# ── KISDataProvider 테스트 ──


class TestKISDataProvider:
    @pytest.mark.asyncio
    @respx.mock
    async def test_token_issuance(self, kis_provider):
        """토큰 발급 테스트"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        token = await kis_provider._ensure_token()
        assert token == "mock_token_12345"
        assert kis_provider._access_token == "mock_token_12345"
        assert kis_provider._token_expires_at is not None
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_reuse(self, kis_provider):
        """유효한 토큰은 재발급하지 않음"""
        route = respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(
            return_value=_token_response()
        )

        await kis_provider._ensure_token()
        await kis_provider._ensure_token()

        assert route.call_count == 1
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_daily_ohlcv(self, kis_provider):
        """국내 일봉 조회"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=_daily_ohlcv_response(
                [
                    ("20240101", 70000, 72000, 69000, 71000, 1000000),
                    ("20240102", 71000, 73000, 70000, 72500, 1200000),
                    ("20240103", 72500, 74000, 72000, 73000, 900000),
                ]
            )
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert df.iloc[0]["open"] == 70000.0
        assert df.iloc[2]["close"] == 73000.0
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_hourly_ohlcv(self, kis_provider):
        """국내 시간봉 조회"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{KR_TIME_PRICE_URL}").mock(
            return_value=_hourly_ohlcv_response(
                [
                    ("20240103", "100000", 72000, 72500, 71500, 72300, 50000),
                    ("20240103", "110000", 72300, 73000, 72000, 72800, 45000),
                ]
            )
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.H1,
            start=datetime(2024, 1, 3, 9, 0),
            end=datetime(2024, 1, 3, 15, 0),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["close"] == 72300.0
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_response(self, kis_provider):
        """빈 응답 처리"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())
        respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": []})
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="999999",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_rate_limit(self, kis_provider):
        """Rate Limit 시 재시도"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        route = respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}")
        route.side_effect = [
            Response(429, json={"rt_cd": "1", "msg1": "Rate limit"}),
            _daily_ohlcv_response(
                [("20240101", 70000, 72000, 69000, 71000, 1000000)]
            ),
        ]

        df = await kis_provider.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
        )

        assert len(df) == 1
        assert route.call_count == 2
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_exhausted_raises(self, kis_provider):
        """최대 재시도 초과 시 예외"""
        from app.utils.exceptions import KISRateLimitError

        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())
        respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=Response(429, json={"rt_cd": "1", "msg1": "Rate limit"})
        )

        with pytest.raises(KISRateLimitError):
            await kis_provider.fetch_ohlcv(
                symbol="005930",
                market=MarketType.KR,
                timeframe=TimeframeType.D1,
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 1),
            )
        await kis_provider.close()


# ── KISDataProvider 미국 주식 테스트 ──


def _us_daily_ohlcv_response(dates_prices):
    """dates_prices: list of (date_str_YYYYMMDD, open, high, low, close, volume)"""
    output2 = []
    for d, o, h, l, c, v in dates_prices:
        output2.append(
            {
                "xymd": d,
                "open": str(o),
                "high": str(h),
                "low": str(l),
                "clos": str(c),
                "tvol": str(v),
            }
        )
    return Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": output2})


def _us_hourly_ohlcv_response(items):
    """items: list of (date_str, time_str_HHMMSS, open, high, low, close, volume)"""
    output2 = []
    for d, t, o, h, l, c, v in items:
        output2.append(
            {
                "xymd": d,
                "xhms": t,
                "open": str(o),
                "high": str(h),
                "low": str(l),
                "clos": str(c),
                "tvol": str(v),
            }
        )
    return Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": output2})


def _us_search_response(symbols):
    """symbols: list of (symbol, name)"""
    output = [{"symb": s, "name": n, "e_sect_name": "Technology"} for s, n in symbols]
    return Response(200, json={"rt_cd": "0", "msg1": "OK", "output": output})


class TestKISDataProviderUS:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_us_daily_ohlcv(self, kis_provider):
        """미국 일봉 조회"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{US_DAILY_PRICE_URL}").mock(
            return_value=_us_daily_ohlcv_response(
                [
                    ("20240102", 185.0, 187.5, 184.0, 186.5, 5000000),
                    ("20240103", 186.5, 188.0, 185.5, 187.0, 4500000),
                    ("20240104", 187.0, 189.0, 186.0, 188.5, 4800000),
                ]
            )
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="AAPL",
            market=MarketType.US,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 2),
            end=datetime(2024, 1, 4),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert df.iloc[0]["open"] == 185.0
        assert df.iloc[2]["close"] == 188.5
        assert df.iloc[0]["volume"] == 5000000
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_us_hourly_ohlcv(self, kis_provider):
        """미국 시간봉 조회"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{US_TIME_PRICE_URL}").mock(
            return_value=_us_hourly_ohlcv_response(
                [
                    ("20240103", "100000", 186.0, 186.5, 185.5, 186.2, 120000),
                    ("20240103", "110000", 186.2, 187.0, 186.0, 186.8, 110000),
                ]
            )
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="AAPL",
            market=MarketType.US,
            timeframe=TimeframeType.H1,
            start=datetime(2024, 1, 3, 9, 0),
            end=datetime(2024, 1, 3, 16, 0),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["close"] == 186.2
        assert df.iloc[1]["volume"] == 110000
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_us_daily_empty(self, kis_provider):
        """미국 일봉 빈 응답"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())
        respx.get(f"{KIS_BASE_URL}{US_DAILY_PRICE_URL}").mock(
            return_value=Response(200, json={"rt_cd": "0", "msg1": "OK", "output2": []})
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="ZZZZ",
            market=MarketType.US,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_us_daily_date_filter(self, kis_provider):
        """미국 일봉 날짜 범위 필터링"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{US_DAILY_PRICE_URL}").mock(
            return_value=_us_daily_ohlcv_response(
                [
                    ("20231229", 180.0, 182.0, 179.0, 181.0, 3000000),  # 범위 밖
                    ("20240102", 185.0, 187.5, 184.0, 186.5, 5000000),  # 범위 안
                    ("20240105", 189.0, 190.0, 188.0, 189.5, 4000000),  # 범위 밖
                ]
            )
        )

        df = await kis_provider.fetch_ohlcv(
            symbol="AAPL",
            market=MarketType.US,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
        )

        assert len(df) == 1
        assert df.iloc[0]["open"] == 185.0
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_us_symbols(self, kis_provider):
        """미국 종목 검색"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        respx.get(f"{KIS_BASE_URL}{US_SEARCH_URL}").mock(
            return_value=_us_search_response(
                [("AAPL", "Apple Inc"), ("AMZN", "Amazon.com Inc")]
            )
        )

        results = await kis_provider.search_symbols(MarketType.US, "A")

        assert len(results) == 2
        assert results[0].symbol == "AAPL"
        assert results[0].name == "Apple Inc"
        assert results[0].market == MarketType.US
        assert results[0].sector == "Technology"
        assert results[1].symbol == "AMZN"
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_us_symbols_api_failure(self, kis_provider):
        """미국 종목 검색 API 실패 시 빈 결과"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())
        respx.get(f"{KIS_BASE_URL}{US_SEARCH_URL}").mock(
            return_value=Response(500, json={"rt_cd": "1", "msg1": "Server Error"})
        )

        results = await kis_provider.search_symbols(MarketType.US, "AAPL")
        assert results == []
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_us_retry_on_rate_limit(self, kis_provider):
        """미국 주식 Rate Limit 재시도"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        route = respx.get(f"{KIS_BASE_URL}{US_DAILY_PRICE_URL}")
        route.side_effect = [
            Response(429, json={"rt_cd": "1", "msg1": "Rate limit"}),
            _us_daily_ohlcv_response(
                [("20240102", 185.0, 187.5, 184.0, 186.5, 5000000)]
            ),
        ]

        df = await kis_provider.fetch_ohlcv(
            symbol="AAPL",
            market=MarketType.US,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 2),
            end=datetime(2024, 1, 2),
        )

        assert len(df) == 1
        assert route.call_count == 2
        await kis_provider.close()


# ── CachedDataProvider 테스트 ──


class TestCachedDataProvider:
    @pytest.mark.asyncio
    @respx.mock
    async def test_cache_miss_then_hit(self, kis_provider, db_session):
        """캐시 미스 → API 호출 → 캐시 저장 → 캐시 히트"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        api_route = respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=_daily_ohlcv_response(
                [
                    ("20240101", 70000, 72000, 69000, 71000, 1000000),
                    ("20240102", 71000, 73000, 70000, 72500, 1200000),
                ]
            )
        )

        cached = CachedDataProvider(kis_provider, db_session)

        # 첫 번째 호출: 캐시 미스 → API 호출
        df1 = await cached.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
        )
        assert len(df1) == 2
        assert api_route.call_count == 1

        # DB에 저장되었는지 확인
        count = db_session.query(MarketData).count()
        assert count == 2

        # 두 번째 호출: 캐시 히트 → API 미호출
        df2 = await cached.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
        )
        assert len(df2) == 2
        assert api_route.call_count == 1  # 추가 호출 없음

        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_cache_expired(self, kis_provider, db_session):
        """TTL 만료된 캐시는 무시하고 API 재호출"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        api_route = respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=_daily_ohlcv_response(
                [("20240101", 70000, 72000, 69000, 71000, 1000000)]
            )
        )

        # 만료된 캐시 데이터 수동 삽입
        expired_record = MarketData(
            id=str(uuid.uuid4()),
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            timestamp=datetime(2024, 1, 1),
            open=70000,
            high=72000,
            low=69000,
            close=71000,
            volume=1000000,
            fetched_at=datetime.utcnow() - timedelta(hours=25),  # 25시간 전 (TTL 24h 초과)
        )
        db_session.add(expired_record)
        db_session.commit()

        cached = CachedDataProvider(kis_provider, db_session)

        df = await cached.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
        )

        assert len(df) == 1
        assert api_route.call_count == 1  # 만료로 인해 API 호출됨
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_cache_upsert(self, kis_provider, db_session):
        """캐시 upsert: 동일 데이터는 업데이트"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())

        # 기존 캐시 삽입
        old_record = MarketData(
            id=str(uuid.uuid4()),
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            timestamp=datetime(2024, 1, 1),
            open=70000,
            high=72000,
            low=69000,
            close=71000,
            volume=1000000,
            fetched_at=datetime.utcnow() - timedelta(hours=25),
        )
        db_session.add(old_record)
        db_session.commit()
        old_id = old_record.id

        respx.get(f"{KIS_BASE_URL}{KR_DAILY_PRICE_URL}").mock(
            return_value=_daily_ohlcv_response(
                [("20240101", 70000, 72000, 69000, 71500, 1100000)]  # close, volume 변경
            )
        )

        cached = CachedDataProvider(kis_provider, db_session)
        await cached.fetch_ohlcv(
            symbol="005930",
            market=MarketType.KR,
            timeframe=TimeframeType.D1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
        )

        # 레코드 수는 여전히 1개 (upsert)
        count = db_session.query(MarketData).count()
        assert count == 1

        updated = db_session.query(MarketData).first()
        assert updated.id == old_id  # 같은 레코드
        assert float(updated.close) == 71500.0  # 값 업데이트됨
        await kis_provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_symbols_delegates(self, kis_provider, db_session):
        """search_symbols는 캐시 없이 직접 프로바이더 호출"""
        respx.post(f"{KIS_BASE_URL}{TOKEN_URL}").mock(return_value=_token_response())
        respx.get(f"{KIS_BASE_URL}{US_SEARCH_URL}").mock(
            return_value=_us_search_response([("AAPL", "Apple Inc")])
        )

        cached = CachedDataProvider(kis_provider, db_session)
        results = await cached.search_symbols(MarketType.US, "AAPL")
        assert len(results) == 1
        assert results[0].symbol == "AAPL"
        await kis_provider.close()
