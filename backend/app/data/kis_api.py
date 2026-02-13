"""한국투자증권 API 클라이언트 (국내 + 미국 주식)"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from app.config import settings
from app.data.provider import DataProvider, SymbolInfo
from app.db.models import MarketType, TimeframeType
from app.utils.exceptions import KISAPIUnavailableError, KISRateLimitError
from app.utils.logger import logger

# KIS API 기본 URL
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 엔드포인트 — 국내
TOKEN_URL = "/oauth2/tokenP"
KR_DAILY_PRICE_URL = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
KR_TIME_PRICE_URL = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
KR_SEARCH_URL = "/uapi/domestic-stock/v1/quotations/search-info"

# 엔드포인트 — 미국
US_DAILY_PRICE_URL = "/uapi/overseas-price/v1/quotations/dailyprice"
US_TIME_PRICE_URL = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
US_SEARCH_URL = "/uapi/overseas-price/v1/quotations/search-info"

# 거래ID — 국내
TR_ID_KR_DAILY = "FHKST03010100"
TR_ID_KR_TIME = "FHKST03010200"
TR_ID_KR_SEARCH = "CTPF1604R"

# 거래ID — 미국
TR_ID_US_DAILY = "HHDFS76240000"
TR_ID_US_TIME = "HHDFS76950200"
TR_ID_US_SEARCH = "CTPF1702R"

# 미국 거래소 코드 (KIS API EXCD 파라미터)
US_EXCHANGE_CODE = "NAS"  # 기본값: 나스닥 (TODO: 종목별 거래소 자동 판별)

# Rate Limit
MAX_REQUESTS_PER_SECOND = 20
MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds


class KISDataProvider(DataProvider):
    """한국투자증권 API 데이터 프로바이더 (국내 + 미국 주식)"""

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        base_url: str = KIS_BASE_URL,
    ):
        self._app_key = app_key or settings.kis_app_key
        self._app_secret = app_secret or settings.kis_app_secret
        self._base_url = base_url
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_SECOND)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── 토큰 관리 ──

    async def _ensure_token(self) -> str:
        """액세스 토큰을 발급하거나, 유효하면 기존 토큰을 반환한다."""
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        client = await self._get_client()
        body = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
        }

        resp = await client.post(TOKEN_URL, json=body)
        if resp.status_code != 200:
            raise KISAPIUnavailableError(f"토큰 발급 실패: {resp.status_code} {resp.text}")

        data = resp.json()
        self._access_token = data["access_token"]
        # KIS 토큰은 보통 24시간 유효
        expires_in = int(data.get("expires_in", 86400))
        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        logger.info("KIS API 토큰 발급 완료 (만료: %s)", self._token_expires_at)
        return self._access_token

    def _common_headers(self, token: str, tr_id: str) -> Dict[str, str]:
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "tr_id": tr_id,
        }

    # ── API 호출 (Rate Limit + 재시도) ──

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        tr_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Rate Limit 세마포어 + exponential backoff 재시도"""
        token = await self._ensure_token()
        headers = self._common_headers(token, tr_id)
        client = await self._get_client()

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            async with self._semaphore:
                try:
                    resp = await client.request(method, url, headers=headers, params=params)

                    if resp.status_code == 429:
                        raise KISRateLimitError()

                    if resp.status_code >= 500:
                        raise KISAPIUnavailableError(
                            f"KIS API 서버 오류: {resp.status_code}"
                        )

                    if resp.status_code != 200:
                        raise KISAPIUnavailableError(
                            f"KIS API 오류: {resp.status_code} {resp.text}"
                        )

                    data = resp.json()
                    # KIS API는 rt_cd="0"이면 성공
                    if data.get("rt_cd") != "0":
                        raise KISAPIUnavailableError(
                            f"KIS API 응답 오류: {data.get('msg1', 'Unknown')}"
                        )

                    return data

                except (KISRateLimitError, KISAPIUnavailableError) as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        wait = BACKOFF_BASE * (2**attempt)
                        logger.warning(
                            "KIS API 재시도 %d/%d (대기 %ds): %s",
                            attempt + 1,
                            MAX_RETRIES,
                            wait,
                            str(e),
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise
                except httpx.HTTPError as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        wait = BACKOFF_BASE * (2**attempt)
                        logger.warning(
                            "HTTP 오류 재시도 %d/%d (대기 %ds): %s",
                            attempt + 1,
                            MAX_RETRIES,
                            wait,
                            str(e),
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise KISAPIUnavailableError(f"HTTP 오류: {str(e)}")

        raise KISAPIUnavailableError(f"최대 재시도 초과: {last_error}")

    # ── OHLCV 조회 ──

    async def fetch_ohlcv(
        self,
        symbol: str,
        market: MarketType,
        timeframe: TimeframeType,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        if market == MarketType.KR:
            if timeframe == TimeframeType.D1:
                return await self._fetch_daily(symbol, start, end)
            else:
                return await self._fetch_hourly(symbol, start, end)
        elif market == MarketType.US:
            if timeframe == TimeframeType.D1:
                return await self._fetch_us_daily(symbol, start, end)
            else:
                return await self._fetch_us_hourly(symbol, start, end)
        else:
            raise ValueError(f"지원하지 않는 시장입니다: {market}")

    async def _fetch_daily(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """국내 주식 일봉 조회"""
        all_rows: List[Dict[str, Any]] = []
        current_end = end

        while current_end >= start:
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": current_end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",  # 일봉
                "FID_ORG_ADJ_PRC": "0",  # 수정주가
            }

            data = await self._request_with_retry(
                "GET", KR_DAILY_PRICE_URL, TR_ID_KR_DAILY, params
            )

            output2 = data.get("output2", [])
            if not output2:
                break

            for item in output2:
                stck_bsop_date = item.get("stck_bsop_date", "")
                if not stck_bsop_date:
                    continue
                row_date = datetime.strptime(stck_bsop_date, "%Y%m%d")
                if row_date < start:
                    continue

                all_rows.append(
                    {
                        "timestamp": row_date,
                        "open": float(item["stck_oprc"]),
                        "high": float(item["stck_hgpr"]),
                        "low": float(item["stck_lwpr"]),
                        "close": float(item["stck_clpr"]),
                        "volume": int(item["acml_vol"]),
                    }
                )

            # 마지막 날짜 이전으로 페이징
            last_date_str = output2[-1].get("stck_bsop_date", "")
            if not last_date_str:
                break
            last_date = datetime.strptime(last_date_str, "%Y%m%d")
            if last_date >= current_end:
                break
            current_end = last_date - timedelta(days=1)

        return self._to_dataframe(all_rows)

    async def _fetch_hourly(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """국내 주식 시간봉 조회"""
        all_rows: List[Dict[str, Any]] = []

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_HOUR_1": end.strftime("%H%M%S"),
            "FID_ETC_CLS_CODE": "",
        }

        data = await self._request_with_retry(
            "GET", KR_TIME_PRICE_URL, TR_ID_KR_TIME, params
        )

        output2 = data.get("output2", [])
        for item in output2:
            stck_cntg_hour = item.get("stck_cntg_hour", "")
            stck_bsop_date = item.get("stck_bsop_date", "")
            if not stck_cntg_hour:
                continue

            if stck_bsop_date:
                ts = datetime.strptime(
                    f"{stck_bsop_date}{stck_cntg_hour}", "%Y%m%d%H%M%S"
                )
            else:
                ts = datetime.strptime(stck_cntg_hour, "%H%M%S").replace(
                    year=end.year, month=end.month, day=end.day
                )

            if ts < start or ts > end:
                continue

            all_rows.append(
                {
                    "timestamp": ts,
                    "open": float(item.get("stck_oprc", 0)),
                    "high": float(item.get("stck_hgpr", 0)),
                    "low": float(item.get("stck_lwpr", 0)),
                    "close": float(item.get("stck_prpr", 0)),
                    "volume": int(item.get("cntg_vol", 0)),
                }
            )

        return self._to_dataframe(all_rows)

    # ── 미국 주식 OHLCV 조회 ──

    async def _fetch_us_daily(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """미국 주식 일봉 조회 (해외주식 기간별 시세 API)"""
        all_rows: List[Dict[str, Any]] = []
        current_end = end

        while current_end >= start:
            params = {
                "AUTH": "",
                "EXCD": US_EXCHANGE_CODE,
                "SYMB": symbol,
                "GUBN": "0",  # 0: 일, 1: 주, 2: 월
                "BYMD": current_end.strftime("%Y%m%d"),
                "MODP": "1",  # 수정주가
            }

            data = await self._request_with_retry(
                "GET", US_DAILY_PRICE_URL, TR_ID_US_DAILY, params
            )

            output2 = data.get("output2", [])
            if not output2:
                break

            for item in output2:
                xymd = item.get("xymd", "")
                if not xymd:
                    continue
                row_date = datetime.strptime(xymd, "%Y%m%d")
                if row_date < start or row_date > end:
                    continue

                all_rows.append(
                    {
                        "timestamp": row_date,
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "close": float(item.get("clos", 0)),
                        "volume": int(item.get("tvol", 0)),
                    }
                )

            # 페이징: 마지막 날짜 이전으로
            last_date_str = output2[-1].get("xymd", "")
            if not last_date_str:
                break
            last_date = datetime.strptime(last_date_str, "%Y%m%d")
            if last_date >= current_end:
                break
            current_end = last_date - timedelta(days=1)

        return self._to_dataframe(all_rows)

    async def _fetch_us_hourly(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """미국 주식 시간봉 조회 (해외주식 분봉 API)"""
        all_rows: List[Dict[str, Any]] = []

        # TODO: KIS 해외주식 분봉 API의 정확한 파라미터는 공식 문서 확인 필요
        params = {
            "AUTH": "",
            "EXCD": US_EXCHANGE_CODE,
            "SYMB": symbol,
            "NMIN": "60",  # 60분봉
            "PINC": "1",
            "NEXT": "",
            "NREC": "120",
            "FILL": "",
            "KEYB": "",
        }

        data = await self._request_with_retry(
            "GET", US_TIME_PRICE_URL, TR_ID_US_TIME, params
        )

        output2 = data.get("output2", [])
        for item in output2:
            xymd = item.get("xymd", "")
            xhms = item.get("xhms", "")
            if not xymd or not xhms:
                continue

            ts = datetime.strptime(f"{xymd}{xhms}", "%Y%m%d%H%M%S")
            if ts < start or ts > end:
                continue

            all_rows.append(
                {
                    "timestamp": ts,
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("clos", 0)),
                    "volume": int(item.get("tvol", 0)),
                }
            )

        return self._to_dataframe(all_rows)

    def _to_dataframe(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    # ── 종목 검색 ──

    async def search_symbols(
        self,
        market: MarketType,
        query: str,
    ) -> List[SymbolInfo]:
        if market == MarketType.KR:
            return await self._search_kr_symbols(query)
        elif market == MarketType.US:
            return await self._search_us_symbols(query)
        else:
            raise ValueError(f"지원하지 않는 시장입니다: {market}")

    async def _search_kr_symbols(self, query: str) -> List[SymbolInfo]:
        """국내 종목 검색"""
        params = {
            "PRDT_TYPE_CD": "300",  # 주식
            "PDNO": query,
        }

        try:
            data = await self._request_with_retry(
                "GET", KR_SEARCH_URL, TR_ID_KR_SEARCH, params
            )
        except Exception:
            logger.warning("국내 종목 검색 API 호출 실패, 빈 결과 반환")
            return []

        output = data.get("output", [])
        results = []
        for item in output:
            results.append(
                SymbolInfo(
                    symbol=item.get("pdno", ""),
                    name=item.get("prdt_name", ""),
                    market=MarketType.KR,
                    sector=item.get("std_indst_clsf_cd_name", None),
                )
            )
        return results

    async def _search_us_symbols(self, query: str) -> List[SymbolInfo]:
        """미국 종목 검색"""
        # TODO: KIS 해외주식 종목 검색 API의 정확한 엔드포인트/파라미터는 공식 문서 확인 필요
        params = {
            "AUTH": "",
            "EXCD": US_EXCHANGE_CODE,
            "CO_YN_PRICECUR": "",
            "FID_COND_MRKT_DIV_CODE": "N",
            "FID_INPUT_ISCD": query,
        }

        try:
            data = await self._request_with_retry(
                "GET", US_SEARCH_URL, TR_ID_US_SEARCH, params
            )
        except Exception:
            logger.warning("미국 종목 검색 API 호출 실패, 빈 결과 반환")
            return []

        output = data.get("output", [])
        results = []
        for item in output:
            results.append(
                SymbolInfo(
                    symbol=item.get("symb", ""),
                    name=item.get("name", ""),
                    market=MarketType.US,
                    sector=item.get("e_sect_name", None),
                )
            )
        return results
