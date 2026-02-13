from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Dict


class MarketConfig(BaseModel):
    """시장별 거래 비용 설정"""

    commission_rate: float  # 매수/매도 각 수수료율
    min_commission: float  # 최소 수수료 (해당 통화 단위)
    slippage_daily: float  # 일봉 슬리피지
    slippage_hourly: float  # 시간봉 슬리피지
    min_order_amount: float  # 최소 주문 금액
    currency: str  # 통화 단위
    trading_days_per_year: int  # 연간 거래일 수


MARKET_CONFIGS: Dict[str, MarketConfig] = {
    "KR": MarketConfig(
        commission_rate=0.00015,  # 0.015%
        min_commission=0,  # 최소 수수료 없음
        slippage_daily=0.001,  # 0.1%
        slippage_hourly=0.0005,  # 0.05%
        min_order_amount=100_000,  # ₩100,000
        currency="KRW",
        trading_days_per_year=245,
    ),
    "US": MarketConfig(
        commission_rate=0.0025,  # 0.25%
        min_commission=1.0,  # $1 최소 수수료
        slippage_daily=0.001,  # 0.1%
        slippage_hourly=0.0005,  # 0.05%
        min_order_amount=100,  # $100
        currency="USD",
        trading_days_per_year=252,
    ),
}


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/quant_backtest"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 한국투자증권 API
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_number: str = ""

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/backtest.log"

    # 캐시 TTL (초)
    cache_ttl_daily: int = 86400  # 일봉: 24시간
    cache_ttl_hourly: int = 21600  # 시간봉: 6시간

    model_config = {"env_file": ".env"}


settings = Settings()
