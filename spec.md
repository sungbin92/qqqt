# 주식 자동투자 백테스팅 시스템

## 1. 개요 (Overview)

- **목적**: 퀀트 기반 주식 투자 전략을 과거 데이터로 검증하고, 전략 파라미터 최적화 및 다중 전략 비교를 통해 수익성 높은 전략을 발굴한다
- **한 줄 요약**: 국내/미국 주식 시장에서 퀀트 전략을 백테스팅하고 상세한 성과 분석 리포트를 제공하는 시스템
- **1차 목표**: 백테스팅 엔진 구축 (실전/모의투자 연동은 2차)
- **사용자**: 단일 사용자 (개인 프로젝트). 인증/인가 없이 운영. 2차 이후 멀티유저 확장 시 인증 추가 검토

## 2. 기술 스택 (Tech Stack)

### Backend (Python)

- **언어**: Python 3.11+
- **웹 프레임워크**: FastAPI
- **ORM**: SQLAlchemy 2.0 + Alembic (마이그레이션)
- **데이터 분석**:
  - NumPy (수치 계산)
  - Pandas (데이터 처리)
  - pandas-ta (기술적 지표, 순수 Python — TA-Lib 대체)
  - SciPy (통계, 최적화)
- **CLI**: Typer + Rich (출력 포맷팅)
- **테스트**: Pytest + pytest-asyncio + pytest-cov
- **비동기 처리**: asyncio, Celery + Redis (백그라운드 작업)
- **API 클라이언트**: httpx (비동기), requests (동기 fallback)
- **검증**: Pydantic v2
- **패키지 관리**: Poetry

> **TA-Lib 미사용 사유**: TA-Lib은 C 라이브러리(ta-lib)를 시스템에 별도 설치해야 하며,
> OS별 설치 방법이 다르고 Docker 빌드 시에도 추가 레이어가 필요하다.
> pandas-ta는 순수 Python으로 동일한 지표를 제공하며 pip install만으로 설치 가능.
> 성능이 병목이 되는 경우 NumPy 벡터화 연산으로 커스텀 지표를 직접 구현한다.

> **Backtrader / VectorBT 미사용**: 설계 참고만 한다.
> Backtrader(이벤트 드리븐 아키텍처), VectorBT(벡터화 연산)의 장점을 참고하여
> 커스텀 엔진을 구축한다. 런타임 의존성에 포함하지 않는다.
> 참고 리포지토리:
>
> - https://github.com/mementum/backtrader (아키텍처)
> - https://github.com/polakowo/vectorbt (벡터화 성능 패턴)
> - https://github.com/kernc/backtesting.py (심플 API 디자인)

### Frontend (TypeScript)

- **언어**: TypeScript
- **프레임워크**: Next.js 14 (App Router) + React
- **스타일링**: Tailwind CSS + shadcn/ui
- **차트**: Recharts 또는 Plotly.js
- **상태 관리**: React Query (TanStack Query)
- **패키지 관리**: pnpm
- **런타임**: Node.js 20+

### Database & Infra

- **DB**: PostgreSQL 15+
- **캐싱 / 메시지 브로커**: Redis (Celery broker + 데이터 캐시)
- **컨테이너**: Docker + docker-compose

## 3. 파일 구조 (File Structure)

```
quant-backtest/
├── backend/                      # Python Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 앱 엔트리포인트
│   │   ├── config.py            # 설정 관리 (Pydantic Settings)
│   │   │
│   │   ├── api/                 # API 라우트
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # 라우터 통합
│   │   │   ├── backtest.py
│   │   │   ├── strategies.py
│   │   │   ├── optimize.py
│   │   │   └── data.py
│   │   │
│   │   ├── engine/              # 백테스팅 엔진
│   │   │   ├── __init__.py
│   │   │   ├── backtest.py      # BacktestEngine 클래스
│   │   │   ├── portfolio.py     # Portfolio 관리
│   │   │   ├── position.py      # Position 클래스
│   │   │   ├── order.py         # Order 실행 로직
│   │   │   └── broker.py        # 수수료, 슬리피지 처리 (MarketConfig 기반)
│   │   │
│   │   ├── strategies/          # 트레이딩 전략
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Strategy 베이스 클래스
│   │   │   ├── mean_reversion.py
│   │   │   └── momentum_breakout.py
│   │   │
│   │   ├── indicators/          # 기술적 지표
│   │   │   ├── __init__.py
│   │   │   ├── technical.py     # MA, RSI, MACD 등 (pandas-ta 래핑)
│   │   │   └── custom.py        # 커스텀 지표 (NumPy 벡터화)
│   │   │
│   │   ├── data/                # 데이터 수집 및 관리
│   │   │   ├── __init__.py
│   │   │   ├── provider.py      # DataProvider 인터페이스 (ABC)
│   │   │   ├── kis_api.py       # 한국투자증권 API 클라이언트 (국내+미국)
│   │   │   ├── cache.py         # 캐싱 레이어 (PostgreSQL + Redis)
│   │   │   └── models.py        # OHLCV 데이터 모델
│   │   │
│   │   ├── analytics/           # 성과 분석
│   │   │   ├── __init__.py
│   │   │   ├── performance.py   # 수익률, 샤프, MDD 등
│   │   │   ├── risk.py          # 리스크 지표
│   │   │   └── report.py        # 리포트 데이터 생성 (차트 데이터 포함)
│   │   │
│   │   ├── optimizer/           # 파라미터 최적화
│   │   │   ├── __init__.py
│   │   │   └── grid_search.py
│   │   │
│   │   ├── worker/              # Celery 워커
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py    # Celery 앱 설정
│   │   │   └── tasks.py         # 비동기 작업 정의
│   │   │
│   │   ├── db/                  # 데이터베이스
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # SQLAlchemy 모델
│   │   │   └── session.py       # DB 세션 관리
│   │   │
│   │   └── utils/               # 유틸리티
│   │       ├── __init__.py
│   │       ├── logger.py
│   │       ├── exceptions.py
│   │       └── response.py      # 통일된 API 응답 헬퍼
│   │
│   ├── cli/                     # CLI 도구 (Typer)
│   │   ├── __init__.py
│   │   ├── main.py              # CLI 엔트리포인트
│   │   └── commands/
│   │       ├── backtest.py
│   │       ├── optimize.py
│   │       └── data.py
│   │
│   ├── tests/                   # 테스트
│   │   ├── unit/
│   │   │   ├── test_engine.py
│   │   │   ├── test_strategy.py
│   │   │   ├── test_performance.py
│   │   │   └── test_broker.py
│   │   ├── integration/
│   │   │   ├── test_api.py
│   │   │   └── test_data_provider.py
│   │   ├── fixtures/
│   │   │   ├── sample_ohlcv.csv        # 삼성전자 3개월 일봉
│   │   │   └── sample_ohlcv_us.csv     # AAPL 3개월 일봉
│   │   └── conftest.py
│   │
│   ├── alembic/                 # DB 마이그레이션
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── notebooks/               # Jupyter 노트북 (분석용)
│   │   └── strategy_research.ipynb
│   │
│   ├── pyproject.toml
│   ├── poetry.lock
│   └── .env.example
│
├── frontend/                    # Next.js Frontend
│   ├── app/
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── backtest/
│   │   │   ├── page.tsx         # 백테스팅 목록
│   │   │   ├── new/page.tsx     # 새 백테스팅
│   │   │   └── [id]/page.tsx    # 결과 상세
│   │   ├── strategies/
│   │   │   └── page.tsx
│   │   ├── optimize/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   │
│   ├── components/
│   │   ├── charts/
│   │   │   ├── EquityCurveChart.tsx
│   │   │   ├── DrawdownChart.tsx
│   │   │   ├── TradeDistribution.tsx
│   │   │   └── MonthlyReturnsHeatmap.tsx
│   │   ├── BacktestForm.tsx
│   │   ├── StrategySelector.tsx
│   │   ├── ResultsCard.tsx
│   │   ├── TradesTable.tsx
│   │   └── JobStatusBanner.tsx  # 비동기 작업 상태 표시
│   │
│   ├── lib/
│   │   ├── api-client.ts        # Backend API 클라이언트
│   │   ├── types.ts             # TypeScript 타입 정의
│   │   └── utils.ts
│   │
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── tsconfig.json
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── docker-compose.yml       # backend + frontend + postgres + redis
│
├── scripts/
│   ├── init_db.py
│   └── download_sample_data.py
│
└── README.md
```

## 4. 데이터 모델 (Data Model)

### SQLAlchemy 모델

```python
# backend/app/db/models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, JSON,
    ForeignKey, BigInteger, UniqueConstraint, Index, Enum as SAEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
from enum import Enum


class Base(DeclarativeBase):
    pass


# ── Enums ──

class MarketType(str, Enum):
    KR = "KR"
    US = "US"

class TimeframeType(str, Enum):
    H1 = "1h"
    D1 = "1d"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── 백테스팅 ──

class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)

    # 전략 설정
    strategy_name = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False)

    # 시장 설정
    market = Column(SAEnum(MarketType), nullable=False)
    symbols = Column(JSON, nullable=False)  # List[str] — ARRAY 대신 JSON (호환성)
    timeframe = Column(SAEnum(TimeframeType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)

    # 비동기 작업 상태
    job_status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_error = Column(String, nullable=True)  # 실패 시 에러 메시지
    progress = Column(Integer, default=0)  # 0~100 진행률

    # 성과 지표 (완료 후 기록)
    total_return = Column(Numeric(10, 4), nullable=True)
    annual_return = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(10, 4), nullable=True)
    profit_factor = Column(Numeric(10, 4), nullable=True)
    total_trades = Column(Integer, default=0)
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    avg_win = Column(Numeric(10, 4), nullable=True)
    avg_loss = Column(Numeric(10, 4), nullable=True)

    # 자산 곡선 (JSON으로 한 번에 저장 — 행 폭발 방지)
    # 형태: [{"timestamp": "...", "equity": 10500.0, "drawdown": -0.02}, ...]
    equity_curve_data = Column(JSON, nullable=True)

    # 관계
    trades = relationship("Trade", back_populates="backtest", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    backtest_id = Column(String, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)

    symbol = Column(String(20), nullable=False)
    side = Column(SAEnum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)

    # 시그널 시점 (전략이 주문을 생성한 봉)
    signal_price = Column(Numeric(15, 4), nullable=False)  # 시그널 시점 종가
    signal_date = Column(DateTime, nullable=False)

    # 실제 체결 (다음 봉 시가 기반)
    fill_price = Column(Numeric(15, 4), nullable=False)  # 체결가 (시가 + 슬리피지)
    fill_date = Column(DateTime, nullable=False)

    # 수수료
    commission = Column(Numeric(15, 4), nullable=False, default=0)

    # 청산 정보 (매도 시 기록)
    exit_signal_price = Column(Numeric(15, 4), nullable=True)
    exit_fill_price = Column(Numeric(15, 4), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_commission = Column(Numeric(15, 4), nullable=True)

    # 손익 (청산 완료 후 계산)
    pnl = Column(Numeric(15, 4), nullable=True)  # 수수료 포함 순손익
    pnl_percent = Column(Numeric(10, 4), nullable=True)
    holding_days = Column(Integer, nullable=True)  # 보유 기간

    backtest = relationship("Backtest", back_populates="trades")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_trades_backtest_symbol", "backtest_id", "symbol"),
    )


class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(1000), nullable=True)
    strategy_type = Column(String(100), nullable=False)
    default_parameters = Column(JSON, nullable=False)
    parameter_schema = Column(JSON, nullable=True)  # 파라미터 범위/타입 정의

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketData(Base):
    """시장 데이터 캐시"""
    __tablename__ = "market_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False)
    market = Column(SAEnum(MarketType), nullable=False)
    timeframe = Column(SAEnum(TimeframeType), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    open = Column(Numeric(15, 4), nullable=False)
    high = Column(Numeric(15, 4), nullable=False)
    low = Column(Numeric(15, 4), nullable=False)
    close = Column(Numeric(15, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)

    fetched_at = Column(DateTime, default=datetime.utcnow)  # 캐시 갱신 시점

    __table_args__ = (
        UniqueConstraint("symbol", "market", "timeframe", "timestamp",
                         name="uq_market_data_identity"),
        Index("ix_market_data_lookup", "symbol", "market", "timeframe", "timestamp"),
    )


class OptimizationResult(Base):
    """파라미터 최적화 결과"""
    __tablename__ = "optimization_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_name = Column(String(100), nullable=False)
    market = Column(SAEnum(MarketType), nullable=False)
    symbols = Column(JSON, nullable=False)
    timeframe = Column(SAEnum(TimeframeType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)

    optimization_metric = Column(String(50), nullable=False)  # "sharpe_ratio" | "total_return" | ...
    total_combinations = Column(Integer, nullable=False)
    parameter_ranges = Column(JSON, nullable=False)

    # 상위 결과 (JSON 배열로 저장)
    # [{"parameters": {...}, "sharpe_ratio": 1.5, "total_return": 0.23, ...}, ...]
    top_results = Column(JSON, nullable=True)

    job_status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_error = Column(String, nullable=True)
    progress = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
```

### 시장별 수수료/슬리피지 설정 (Config)

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Dict


class MarketConfig(BaseModel):
    """시장별 거래 비용 설정"""
    commission_rate: float       # 매수/매도 각 수수료율
    min_commission: float        # 최소 수수료 (해당 통화 단위)
    slippage_daily: float        # 일봉 슬리피지
    slippage_hourly: float       # 시간봉 슬리피지
    min_order_amount: float      # 최소 주문 금액
    currency: str                # 통화 단위
    trading_days_per_year: int   # 연간 거래일 수


MARKET_CONFIGS: Dict[str, MarketConfig] = {
    "KR": MarketConfig(
        commission_rate=0.00015,       # 0.015%
        min_commission=0,              # 최소 수수료 없음
        slippage_daily=0.001,          # 0.1%
        slippage_hourly=0.0005,        # 0.05%
        min_order_amount=100_000,      # ₩100,000
        currency="KRW",
        trading_days_per_year=245,
    ),
    "US": MarketConfig(
        commission_rate=0.0025,        # 0.25%
        min_commission=1.0,            # $1 최소 수수료
        slippage_daily=0.001,          # 0.1%
        slippage_hourly=0.0005,        # 0.05%
        min_order_amount=100,          # $100
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
    cache_ttl_daily: int = 86400      # 일봉: 24시간
    cache_ttl_hourly: int = 21600     # 시간봉: 6시간

    class Config:
        env_file = ".env"
```

### Pydantic 스키마 (API 요청/응답)

```python
# backend/app/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.db.models import MarketType, TimeframeType, JobStatus


# ── 통일된 API 응답 래퍼 ──

class ApiResponse(BaseModel):
    """모든 API 응답의 공통 래퍼"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── 백테스팅 ──

class BacktestCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    strategy_name: str
    parameters: Dict[str, Any]
    market: MarketType
    symbols: List[str] = Field(..., min_length=1, max_length=100)
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Field(..., gt=0)


class BacktestSummary(BaseModel):
    id: str
    name: str
    strategy_name: str
    market: MarketType
    symbols: List[str]
    job_status: JobStatus
    total_return: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    total_trades: int
    created_at: datetime

    class Config:
        from_attributes = True


class BacktestDetail(BaseModel):
    id: str
    name: str
    description: Optional[str]
    strategy_name: str
    parameters: Dict[str, Any]
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal

    job_status: JobStatus
    job_error: Optional[str]
    progress: int

    # 성과 지표
    total_return: Optional[Decimal]
    annual_return: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    sortino_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    win_rate: Optional[Decimal]
    profit_factor: Optional[Decimal]
    total_trades: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_win: Optional[Decimal]
    avg_loss: Optional[Decimal]

    equity_curve_data: Optional[List[Dict[str, Any]]]
    trades: List['TradeResponse']
    created_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: int
    signal_price: Decimal
    signal_date: datetime
    fill_price: Decimal
    fill_date: datetime
    commission: Decimal
    exit_fill_price: Optional[Decimal]
    exit_date: Optional[datetime]
    exit_commission: Optional[Decimal]
    pnl: Optional[Decimal]
    pnl_percent: Optional[Decimal]
    holding_days: Optional[int]

    class Config:
        from_attributes = True


# ── 최적화 ──

class OptimizeCreate(BaseModel):
    strategy_name: str
    parameter_ranges: Dict[str, Dict[str, float]]  # {"param": {"min": 10, "max": 30, "step": 5}}
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    optimization_metric: str = "sharpe_ratio"


# ── 비동기 작업 ──

class JobResponse(BaseModel):
    """비동기 작업 생성 응답"""
    job_id: str
    status: JobStatus
    message: str
```

## 5. API 엔드포인트 (API Endpoints)

### 통일된 응답 형식

모든 API는 `ApiResponse` 래퍼를 사용한다:

```json
// 성공
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "total": 42 },
  "timestamp": "2024-01-15T10:30:00Z"
}

// 에러
{
  "success": false,
  "error": "시작일이 종료일보다 미래입니다",
  "error_code": "INVALID_DATE_RANGE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 백테스팅

| Method | Path                     | 설명                  | 비동기 | Request / Params | Response                          |
| ------ | ------------------------ | --------------------- | ------ | ---------------- | --------------------------------- |
| POST   | /api/backtest            | 백테스팅 작업 생성    | ✅     | BacktestCreate   | JobResponse (job_id 반환)         |
| GET    | /api/backtest            | 백테스팅 목록         |        | ?page=1&limit=20 | { data: BacktestSummary[], meta } |
| GET    | /api/backtest/:id        | 상세 조회 (결과 포함) |        | -                | BacktestDetail                    |
| GET    | /api/backtest/:id/status | 작업 진행 상태 폴링   |        | -                | { status, progress }              |
| DELETE | /api/backtest/:id        | 삭제                  |        | -                | { success: true }                 |
| GET    | /api/backtest/:id/export | CSV 다운로드          |        | -                | CSV file (StreamingResponse)      |

### 전략

| Method | Path                      | 설명                | Request          | Response           |
| ------ | ------------------------- | ------------------- | ---------------- | ------------------ |
| GET    | /api/strategies           | 사용 가능 전략 목록 | -                | StrategyInfo[]     |
| GET    | /api/strategies/templates | 저장된 템플릿 목록  | -                | StrategyTemplate[] |
| POST   | /api/strategies/templates | 템플릿 저장         | StrategyTemplate | StrategyTemplate   |

### 최적화

| Method | Path                     | 설명                | 비동기 | Request        | Response             |
| ------ | ------------------------ | ------------------- | ------ | -------------- | -------------------- |
| POST   | /api/optimize            | 최적화 작업 생성    | ✅     | OptimizeCreate | JobResponse          |
| GET    | /api/optimize/:id        | 최적화 결과 조회    |        | -              | OptimizationResult   |
| GET    | /api/optimize/:id/status | 작업 진행 상태 폴링 |        | -              | { status, progress } |

### 데이터

| Method | Path              | 설명           | Params                                   | Response |
| ------ | ----------------- | -------------- | ---------------------------------------- | -------- |
| GET    | /api/data/symbols | 종목 검색      | ?market=KR&query=삼성                    | Symbol[] |
| GET    | /api/data/ohlcv   | 과거 시세 조회 | ?symbol=005930&market=KR&from=...&to=... | OHLCV[]  |

## 6. 핵심 기능 요구사항 (Requirements)

### 필수 (Must Have)

- [ ] **백테스팅 엔진**
  - [ ] 단일 종목 백테스팅
  - [ ] 포트폴리오 백테스팅 (다중 종목 동시 운용)
  - [ ] 롱 포지션 지원 (숏은 2차)
  - [ ] MarketConfig 기반 수수료 및 슬리피지 계산
  - [ ] 시그널 → 다음봉 시가 체결 파이프라인
  - [ ] 포지션 한도 강제 (엔진 레벨, 아래 비즈니스 로직 참고)
- [ ] **비동기 작업 처리**
  - [ ] Celery 기반 백테스팅 비동기 실행
  - [ ] 진행률 업데이트 (DB progress 필드)
  - [ ] 작업 상태 폴링 API
  - [ ] 실패 시 에러 메시지 저장
- [ ] **데이터 수집 및 관리**
  - [ ] 한국투자증권 API 연동 (국내 주식)
  - [ ] 한국투자증권 API 연동 (미국 주식) — 해외주식 시세 API 사용
  - [ ] 일봉/시간봉 데이터 수집
  - [ ] PostgreSQL 캐싱 + UniqueConstraint
- [ ] **성과 분석**
  - [ ] 총 수익률 (Total Return)
  - [ ] 연환산 수익률 (CAGR)
  - [ ] 샤프 비율 (Sharpe Ratio)
  - [ ] 소르티노 비율 (Sortino Ratio)
  - [ ] 최대 낙폭 (MDD)
  - [ ] 승률, 평균 수익/손실
  - [ ] 최대 연속 승/패
  - [ ] Profit Factor
- [ ] **전략 구현**
  - [ ] Strategy 베이스 클래스 (다중 종목 지원)
  - [ ] 예제 전략 1: 평균회귀 (Mean Reversion)
  - [ ] 예제 전략 2: 모멘텀 돌파 (Momentum Breakout)
- [ ] **CLI 인터페이스** (Typer)
  - [ ] `backtest run` — 백테스팅 실행
  - [ ] `backtest list` — 과거 목록
  - [ ] `backtest show <id>` — 결과 상세
  - [ ] `strategy list` — 전략 목록
  - [ ] `data download` — 데이터 수집
- [ ] **웹 대시보드**
  - [ ] 백테스팅 설정 폼
  - [ ] 결과 대시보드 (성과 지표 카드 + 작업 상태)
  - [ ] 자산 곡선 / 낙폭 차트
  - [ ] 거래 내역 테이블
  - [ ] CSV 다운로드

### 선택 (Nice to Have)

- [ ] 파라미터 최적화 (Grid Search + 히트맵)
- [ ] 다중 전략 비교 (동일 조건, 성과 비교 차트)
- [ ] 커스텀 지표 생성
- [ ] 월별 수익 히트맵

## 7. UI/UX 요구사항

### CLI (Typer + Rich)

- **명령어 구조**: `poetry run python -m cli.main <command> [options]`
- **출력 형식**:
  - 진행 상황: Rich Progress bar
  - 결과: Rich Table (컬러 출력)
  - 에러: 명확한 에러 메시지 + 해결 제안

```bash
# 실행 예시
poetry run python -m cli.main backtest run \
  --strategy MeanReversion \
  --symbol 005930 \
  --market KR \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --capital 10000000

poetry run python -m cli.main backtest list
poetry run python -m cli.main backtest show abc-123-def

poetry run python -m cli.main optimize \
  --strategy MeanReversion \
  --param lookback_period:10:30:5 \
  --param entry_threshold:1.5:3.0:0.5 \
  --symbol 005930 --market KR

poetry run python -m cli.main data download \
  --symbol 005930 --market KR \
  --start 2020-01-01 --end 2023-12-31
```

### Web Dashboard

- **레이아웃**: 상단 네비게이션 + 좌측 사이드바 + 메인 콘텐츠
- **반응형**: 데스크탑 우선, 태블릿(768px+) 사용 가능, 모바일은 기본 조회만
- **주요 페이지**:
  - `/dashboard` — 최근 백테스팅 요약 + 실행 중인 작업 상태
  - `/backtest/new` — 새 백테스팅 생성 폼
  - `/backtest/:id` — 결과 상세 (작업 완료 전이면 진행률 표시)
  - `/strategies` — 전략 목록 및 템플릿 관리
  - `/optimize` — 파라미터 최적화 (선택)
- **차트**:
  - 자산 곡선 (Equity Curve): 라인 차트
  - 낙폭 (Drawdown): 영역 차트 (빨간색)
  - 거래 분포: 히스토그램
  - 월별 수익: 히트맵 (선택)

## 8. 비즈니스 로직 / 규칙 (Business Rules)

### 주문 실행 파이프라인

백테스팅의 주문 실행은 **시그널-체결 분리 모델**을 따른다:

```
1. 현재 봉(t) 완성 → 전략의 on_bar() 호출
2. 전략이 PendingOrder 생성 (signal_price = 봉(t)의 close)
3. 다음 봉(t+1) 도착
4. 체결가 결정: fill_price = 봉(t+1)의 open × (1 + slippage)
   - 매수: slippage 양수 (불리하게)
   - 매도: slippage 음수 (불리하게)
5. 수수료 계산: commission = fill_price × quantity × commission_rate
   - commission < min_commission 이면 min_commission 적용
6. 포지션 한도 검증 (아래 참고)
7. 검증 통과 시 체결, 실패 시 주문 취소 (로그 기록)
```

전략의 `on_bar()`는 **현재 봉까지의 데이터만** 접근 가능하며, 체결가는 엔진이 결정한다.
전략은 수량을 "최대 투자 비율"로 요청하고, 엔진이 다음 봉 시가 기준으로 실제 수량을 계산한다.

```python
# 전략에서 주문 생성 (수량이 아닌 비율로 요청)
def on_bar(self, bars: Dict[str, pd.Series], portfolio: Portfolio) -> List[PendingOrder]:
    return [PendingOrder(
        symbol="005930",
        side=OrderSide.BUY,
        weight=0.3,  # 포트폴리오의 30% 투자
    )]

# 엔진이 다음 봉 시가 기준으로 수량 확정
# actual_quantity = floor(portfolio.equity * weight / next_open_price)
```

### 포지션 한도 (엔진 레벨 강제)

포지션 한도는 전략이 아닌 **엔진(Broker)**이 강제한다. 전략은 원하는 만큼 주문을 내지만, 아래 제약을 위반하면 엔진이 주문을 거부/축소한다.

| 규칙             | 값                            | 설명                                        |
| ---------------- | ----------------------------- | ------------------------------------------- |
| 종목당 최대 비중 | 포트폴리오 평가액의 40%       | 단일 종목 집중 리스크 방지                  |
| 최대 포지션 수   | symbols 배열 길이             | 설정된 유니버스 내에서만 거래               |
| 최소 주문 금액   | MarketConfig.min_order_amount | KR: ₩100,000 / US: $100                     |
| 최소 잔여 현금   | 포트폴리오 평가액의 5%        | 수수료 여유분 확보                          |
| 정수 수량        | 소수점 이하 버림              | 국내 주식은 1주 단위 (미국도 동일하게 처리) |

위 값들은 `config.py`에서 오버라이드 가능하게 설계한다.

### 백테스팅 실행 규칙

- 시작일 < 종료일
- 최소 기간: 30일(일봉), 7일(시간봉)
- 초기 자본금 최소: KR ₩1,000,000 / US $1,000
- 최대 종목 수: 100개

### 데이터 캐싱 규칙

- 일봉: 24시간 TTL
- 시간봉: 6시간 TTL
- 캐시 미스 시 한국투자증권 API 호출
- MarketData 테이블의 `fetched_at`으로 만료 판단

### 최적화 규칙

- Grid Search 최대 조합 수: 10,000
- 초과 시 에러 반환 (사용자가 범위 조정)
- 결과는 최적화 메트릭 기준 상위 10개 저장

## 9. 에러 처리 (Error Handling)

### 에러 코드 정의

| HTTP | 코드                  | 설명                       |
| ---- | --------------------- | -------------------------- |
| 400  | INVALID_DATE_RANGE    | 시작일이 종료일보다 미래   |
| 400  | PERIOD_TOO_SHORT      | 최소 백테스팅 기간 미달    |
| 400  | INSUFFICIENT_CAPITAL  | 최소 자본금 미달           |
| 400  | TOO_MANY_COMBINATIONS | 최적화 조합 수 초과        |
| 400  | INSUFFICIENT_DATA     | 해당 기간 데이터 부족      |
| 404  | BACKTEST_NOT_FOUND    | 백테스팅 ID 없음           |
| 404  | STRATEGY_NOT_FOUND    | 전략 이름 없음             |
| 429  | KIS_RATE_LIMIT        | 한국투자증권 API 호출 제한 |
| 500  | ENGINE_ERROR          | 백테스팅 엔진 내부 오류    |
| 503  | KIS_API_UNAVAILABLE   | 한국투자증권 API 응답 없음 |

### 에러 처리 전략

- 한국투자증권 API 호출 실패: 3회 재시도 (exponential backoff: 1s, 2s, 4s)
- Rate Limit 초과: 대기 후 재시도 (Retry-After 헤더 참조)
- 데이터 누락: 에러 메시지에 누락 구간 명시
- 백테스팅 중 오류: 부분 결과 저장 + job_status=FAILED + job_error 기록
- CLI: exit code 1 + Rich 에러 패널 출력
- Web: Toast 알림 + 에러 상태 표시

## 10. 제약 사항 / 주의 사항 (Constraints)

### 런타임 요구사항

| 구성 요소  | 버전                         |
| ---------- | ---------------------------- |
| Python     | 3.11+                        |
| Node.js    | 20+ (프론트엔드 빌드/실행용) |
| PostgreSQL | 15+                          |
| Redis      | 7+                           |

### 한국투자증권 API

- KIS Developers 가입 필수 (https://apiportal.koreainvestment.com)
- **국내 주식 시세**: 주식현재가 시세, 주식현재가 일자별 API 사용
- **미국 주식 시세**: 해외주식 현재가 상세, 해외주식 기간별 시세 API 사용
  - 미국 주식 API 엔드포인트와 요청 형식은 국내와 다름 → `kis_api.py`에서 market별 분기 처리
  - **구현 전 KIS API 문서에서 해외주식 시세 조회 API의 정확한 엔드포인트, 요청 파라미터, 응답 형식을 확인할 것**
  - API 문서: https://apiportal.koreainvestment.com → 해외주식 → 시세 관련 API
- Rate Limit: 초당 최대 20건, 일일 최대 10,000건
- 데이터 범위: 일봉 최근 ~5년, 시간봉 최근 ~1년 (API 제한에 따라 다를 수 있음)

### 성능

- 백테스팅은 Celery 워커에서 비동기 실행
- 대량 데이터 처리 시 Pandas chunked read 또는 NumPy 벡터화 활용
- 포트폴리오 백테스팅: 종목 수 × 기간에 비례하여 처리 시간 증가

### 보안

- API 키는 환경변수로만 관리 (.env)
- API 키 프론트엔드 노출 금지
- 단일 사용자 모드이므로 인증 미구현 (2차에서 추가 검토)

### 코드 품질

- Python: mypy 타입 힌팅 + Pydantic 모델 활용
- TypeScript: strict 모드
- 테스트 커버리지 최소 70%
- Black (포맷터) + Ruff (린터) 사용
- Git commit 전 lint + 테스트 통과 필수

## 11. 테스트 요구사항 (Testing)

### 단위 테스트 (Pytest)

- [ ] 백테스팅 엔진
  - [ ] Portfolio (포지션 추가/제거, 잔고, 평가액)
  - [ ] Broker (수수료 계산 — KR/US 각각, 슬리피지, 포지션 한도 검증)
  - [ ] Order 실행 (시그널→체결 파이프라인, 수량 확정)
- [ ] 성과 분석
  - [ ] PerformanceMetrics (NumPy 벡터화 연산 검증)
  - [ ] 엣지 케이스: 거래 0건, 전부 수익, 전부 손실
- [ ] 전략
  - [ ] 시그널 생성 (다중 종목 히스토리 분리 검증)
  - [ ] 지표 계산 (pandas-ta 래핑 검증)
  - [ ] 엣지 케이스: 데이터 부족, 표준편차 0

### 통합 테스트

- [ ] API 엔드포인트 (FastAPI TestClient)
  - [ ] POST /api/backtest → JobResponse 반환 확인
  - [ ] GET /api/backtest/:id → 완료된 결과 조회
  - [ ] 에러 케이스: 잘못된 날짜, 없는 전략 등
- [ ] 데이터 프로바이더
  - [ ] KIS API Mock (pytest-mock / respx)
  - [ ] 캐시 히트/미스 동작
  - [ ] Rate Limit 재시도 로직

### 테스트 데이터

- `tests/fixtures/sample_ohlcv.csv`: 삼성전자 3개월 일봉
- `tests/fixtures/sample_ohlcv_us.csv`: AAPL 3개월 일봉
- conftest.py에서 Pandas DataFrame 픽스처 제공

### 실행

```bash
poetry run pytest                                    # 전체
poetry run pytest --cov=app --cov-report=html       # 커버리지
poetry run pytest tests/unit/test_broker.py          # 특정 파일
poetry run pytest -m "not slow"                      # 느린 테스트 제외
```

## 12. 참고 자료 (References)

### 외부 API

- 한국투자증권 KIS Developers: https://apiportal.koreainvestment.com
  - 국내주식 시세 API
  - **해외주식 시세 API** (미국 주식 데이터 수집에 사용)

### 기술 문서

- FastAPI: https://fastapi.tiangolo.com
- SQLAlchemy 2.0: https://docs.sqlalchemy.org
- Celery: https://docs.celeryq.dev
- Pandas: https://pandas.pydata.org/docs
- NumPy: https://numpy.org/doc
- pandas-ta: https://github.com/twopirllc/pandas-ta
- Typer: https://typer.tiangolo.com
- Rich: https://rich.readthedocs.io
- Next.js 14: https://nextjs.org/docs
- Recharts: https://recharts.org

### 설계 참고 (런타임 의존성 아님)

- Backtrader: https://github.com/mementum/backtrader — 이벤트 드리븐 아키텍처
- VectorBT: https://github.com/polakowo/vectorbt — 벡터화 성능 패턴
- Backtesting.py: https://github.com/kernc/backtesting.py — 심플 API 디자인

### 퀀트 전략 자료

- "Quantitative Trading" by Ernest Chan
- "Python for Finance" by Yves Hilpisch

---

## 추가 구현 가이드

### 전략 베이스 클래스 (다중 종목 지원)

```python
# backend/app/strategies/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class PendingOrder:
    """
    전략이 생성하는 주문 요청.
    수량은 weight(비율)로 지정하고, 엔진이 다음 봉 시가 기준으로 실제 수량을 확정한다.
    """
    symbol: str
    side: OrderSide
    weight: float  # 포트폴리오 평가액 대비 투자 비율 (0.0 ~ 1.0)
    reason: Optional[str] = None  # 매매 사유 (로깅용)


class Strategy(ABC):
    """
    전략 베이스 클래스.

    - 다중 종목을 지원하기 위해 bars는 Dict[symbol, pd.Series]로 전달
    - 종목별 상태는 self._state[symbol]에 저장
    """

    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name = self.__class__.__name__
        self._state: Dict[str, Dict[str, Any]] = {}  # 종목별 내부 상태

    def _get_state(self, symbol: str) -> Dict[str, Any]:
        """종목별 상태 초기화 및 반환"""
        if symbol not in self._state:
            self._state[symbol] = self._init_state()
        return self._state[symbol]

    def _init_state(self) -> Dict[str, Any]:
        """종목별 초기 상태. 서브클래스에서 오버라이드."""
        return {"price_history": [], "volume_history": []}

    @abstractmethod
    def on_bar(
        self,
        bars: Dict[str, pd.Series],  # {symbol: OHLCV Series}
        portfolio: 'Portfolio',
    ) -> List[PendingOrder]:
        """
        새로운 봉이 도착할 때 호출.

        Args:
            bars: 현재 시점의 각 종목 OHLCV 데이터
            portfolio: 현재 포트폴리오 상태 (읽기 전용으로 사용)

        Returns:
            실행할 PendingOrder 리스트.
            엔진이 다음 봉 시가 기준으로 체결 여부를 결정한다.
        """
        pass
```

### 평균회귀 전략 (다중 종목 지원)

```python
# backend/app/strategies/mean_reversion.py
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from .base import Strategy, PendingOrder, OrderSide


class MeanReversionStrategy(Strategy):
    """
    평균회귀 전략.
    가격이 이동평균에서 일정 Z-Score 이상 벗어나면 평균 회귀를 기대하고 진입.
    종목별로 독립적인 상태를 유지한다.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "lookback_period": 20,
            "entry_threshold": 2.0,   # 진입 Z-Score
            "exit_threshold": 0.5,    # 청산 Z-Score
            "position_weight": 0.3,   # 종목당 투자 비율
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: 'Portfolio'
    ) -> List[PendingOrder]:
        orders = []
        lookback = self.parameters["lookback_period"]

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            state["price_history"].append(close)

            if len(state["price_history"]) < lookback:
                continue

            prices = np.array(state["price_history"][-lookback:])
            mean = np.mean(prices)
            std = np.std(prices)

            if std == 0:
                continue

            z_score = (close - mean) / std
            position = portfolio.get_position(symbol)

            # 과매도 → 매수
            if z_score < -self.parameters["entry_threshold"] and position is None:
                orders.append(PendingOrder(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    weight=self.parameters["position_weight"],
                    reason=f"Z-Score={z_score:.2f} < -{self.parameters['entry_threshold']}",
                ))

            # 평균 회귀 → 매도
            elif position and z_score > -self.parameters["exit_threshold"]:
                orders.append(PendingOrder(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    weight=1.0,  # 전량 매도 (해당 종목 포지션의 100%)
                    reason=f"Z-Score={z_score:.2f} > -{self.parameters['exit_threshold']}",
                ))

        return orders
```

### Broker (수수료/슬리피지/포지션 한도)

```python
# backend/app/engine/broker.py
import math
from typing import Optional, Tuple
from app.config import MarketConfig, MARKET_CONFIGS
from app.db.models import TimeframeType


class Broker:
    """
    주문 체결 처리.
    MarketConfig 기반으로 수수료/슬리피지를 계산하고,
    포지션 한도를 엔진 레벨에서 강제한다.
    """

    # 포지션 한도 기본값 (config로 오버라이드 가능)
    MAX_POSITION_WEIGHT = 0.40      # 종목당 최대 40%
    MIN_CASH_RESERVE_RATIO = 0.05   # 최소 잔여 현금 5%

    def __init__(self, market: str, timeframe: TimeframeType):
        self.config: MarketConfig = MARKET_CONFIGS[market]
        self.timeframe = timeframe

    def get_slippage(self) -> float:
        if self.timeframe == TimeframeType.D1:
            return self.config.slippage_daily
        return self.config.slippage_hourly

    def calculate_fill_price(self, next_open: float, side: str) -> float:
        """다음 봉 시가 + 슬리피지로 체결가 결정"""
        slippage = self.get_slippage()
        if side == "BUY":
            return next_open * (1 + slippage)  # 매수: 불리하게
        return next_open * (1 - slippage)      # 매도: 불리하게

    def calculate_commission(self, fill_price: float, quantity: int) -> float:
        """수수료 계산"""
        raw = fill_price * quantity * self.config.commission_rate
        return max(raw, self.config.min_commission)

    def calculate_quantity(
        self,
        portfolio_equity: float,
        weight: float,
        fill_price: float,
        current_position_value: float = 0,
    ) -> int:
        """
        투자 비율(weight)과 체결가로 실제 수량 확정.
        포지션 한도를 적용하여 수량을 축소할 수 있다.
        """
        target_value = portfolio_equity * weight

        # 1) 종목당 최대 비중 검증
        max_value = portfolio_equity * self.MAX_POSITION_WEIGHT
        allowed_value = max_value - current_position_value
        target_value = min(target_value, allowed_value)

        # 2) 최소 잔여 현금 확보
        # (실제 available cash는 엔진에서 전달받아 검증)

        # 3) 최소 주문 금액 검증
        if target_value < self.config.min_order_amount:
            return 0

        # 4) 정수 수량 (소수점 버림)
        quantity = math.floor(target_value / fill_price)
        return max(quantity, 0)

    def validate_order(
        self,
        portfolio_equity: float,
        available_cash: float,
        fill_price: float,
        quantity: int,
    ) -> Tuple[bool, Optional[str]]:
        """주문 최종 검증"""
        order_value = fill_price * quantity
        commission = self.calculate_commission(fill_price, quantity)
        total_cost = order_value + commission

        # 현금 부족
        if total_cost > available_cash:
            return False, "INSUFFICIENT_CASH"

        # 최소 잔여 현금 확보
        remaining = available_cash - total_cost
        if remaining < portfolio_equity * self.MIN_CASH_RESERVE_RATIO:
            return False, "CASH_RESERVE_VIOLATION"

        # 최소 주문 금액
        if order_value < self.config.min_order_amount:
            return False, "BELOW_MIN_ORDER"

        return True, None
```

### 성과 분석 (NumPy 벡터화)

```python
# backend/app/analytics/performance.py
import numpy as np
import pandas as pd


class PerformanceMetrics:
    """성과 지표 계산 (벡터화 연산)"""

    @staticmethod
    def calculate_returns(equity_curve: pd.Series) -> pd.Series:
        return equity_curve.pct_change().fillna(0)

    @staticmethod
    def total_return(equity_curve: pd.Series) -> float:
        return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    @staticmethod
    def annual_return(equity_curve: pd.Series, trading_days: int = 252) -> float:
        total_days = len(equity_curve)
        years = total_days / trading_days
        total_ret = PerformanceMetrics.total_return(equity_curve)
        if years <= 0:
            return 0
        return (1 + total_ret) ** (1 / years) - 1

    @staticmethod
    def sharpe_ratio(equity_curve: pd.Series, risk_free_rate: float = 0.02,
                     trading_days: int = 252) -> float:
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        excess = returns - risk_free_rate / trading_days
        if returns.std() == 0:
            return 0
        return np.sqrt(trading_days) * excess.mean() / returns.std()

    @staticmethod
    def sortino_ratio(equity_curve: pd.Series, risk_free_rate: float = 0.02,
                      trading_days: int = 252) -> float:
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        excess = returns - risk_free_rate / trading_days
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 0
        return np.sqrt(trading_days) * excess.mean() / downside.std()

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        cummax = equity_curve.expanding().max()
        dd = (equity_curve - cummax) / cummax
        return abs(dd.min())

    @staticmethod
    def win_rate(trades: pd.DataFrame) -> float:
        if len(trades) == 0:
            return 0
        return (trades["pnl"] > 0).sum() / len(trades)

    @staticmethod
    def profit_factor(trades: pd.DataFrame) -> float:
        if len(trades) == 0:
            return 0
        gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(trades[trades["pnl"] < 0]["pnl"].sum())
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0
        return gross_profit / gross_loss

    @staticmethod
    def max_consecutive(trades: pd.DataFrame, win: bool = True) -> int:
        """최대 연속 승/패"""
        if len(trades) == 0:
            return 0
        results = (trades["pnl"] > 0) if win else (trades["pnl"] <= 0)
        max_streak = current = 0
        for r in results:
            if r:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak
```

### pyproject.toml

```toml
[tool.poetry]
name = "quant-backtest"
version = "0.1.0"
description = "Quantitative Trading Backtesting System"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.25"
alembic = "^1.13.1"
psycopg2-binary = "^2.9.9"
pydantic = "^2.5.3"
pydantic-settings = "^2.1.0"
numpy = "^1.26.3"
pandas = "^2.1.4"
pandas-ta = "^0.3.14b1"
scipy = "^1.11.4"
httpx = "^0.26.0"
typer = {extras = ["all"], version = "^0.9.0"}
rich = "^13.7.0"
celery = {extras = ["redis"], version = "^5.3.6"}
redis = "^5.0.1"
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
respx = "^0.20.2"
black = "^23.12.1"
ruff = "^0.1.11"
mypy = "^1.8.0"
ipython = "^8.19.0"
jupyter = "^1.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --cov=app --cov-report=html"
markers = ["slow: marks tests as slow"]
```

### .env.example

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/quant_backtest

# Redis (Celery broker + 캐시)
REDIS_URL=redis://localhost:6379/0

# 한국투자증권 API
# KIS Developers 가입: https://apiportal.koreainvestment.com
# 국내 + 해외(미국) 주식 시세 조회에 사용
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_ACCOUNT_NUMBER=your_account_number

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/backtest.log

# 캐시 TTL (초)
CACHE_TTL_DAILY=86400
CACHE_TTL_HOURLY=21600
```

---

## 개발 우선순위

### Phase 1: 핵심 엔진

1. 프로젝트 구조 설정 (backend: Poetry, frontend: pnpm)
2. SQLAlchemy 모델 작성 + Alembic 마이그레이션
3. MarketConfig (KR/US 수수료/슬리피지 설정)
4. 백테스팅 엔진 핵심 (Portfolio, Broker, Order 파이프라인)
5. 시그널→다음봉시가 체결 로직
6. 성과 분석 모듈 (PerformanceMetrics)
7. Strategy 베이스 클래스 + 예제 전략 1개
8. 단위 테스트

### Phase 2: 데이터 + CLI

1. 한국투자증권 API 클라이언트 (국내)
2. 한국투자증권 API 클라이언트 (미국) — 해외주식 시세 API
3. 데이터 캐싱 (PostgreSQL)
4. CLI 명령어 구현 (Typer + Rich)
5. 예제 전략 2번째 추가

### Phase 3: 비동기 + API

1. Celery 워커 설정 + Redis
2. FastAPI 엔드포인트 (비동기 작업 생성/폴링)
3. 통일된 ApiResponse 래퍼
4. 통합 테스트
5. Docker Compose (backend + postgres + redis)

### Phase 4: 웹 대시보드

1. Next.js 프로젝트 설정
2. API 클라이언트 (TypeScript)
3. 백테스팅 폼 + 작업 상태 폴링 UI
4. 결과 대시보드 (성과 카드 + 차트)
5. 거래 내역 테이블 + CSV 다운로드

### Phase 5: 고급 기능

1. 파라미터 최적화 (Grid Search)
2. 포트폴리오 백테스팅 다중 종목
3. 다중 전략 비교
