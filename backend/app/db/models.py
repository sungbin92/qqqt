import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship


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
    symbols = Column(JSON, nullable=False)  # List[str]
    timeframe = Column(SAEnum(TimeframeType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)

    # 비동기 작업 상태
    job_status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_error = Column(String, nullable=True)
    progress = Column(Integer, default=0)

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

    # 자산 곡선
    equity_curve_data = Column(JSON, nullable=True)

    # 관계
    trades = relationship("Trade", back_populates="backtest", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    backtest_id = Column(
        String, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False
    )

    symbol = Column(String(20), nullable=False)
    side = Column(SAEnum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)

    # 시그널 시점
    signal_price = Column(Numeric(15, 4), nullable=False)
    signal_date = Column(DateTime, nullable=False)

    # 실제 체결
    fill_price = Column(Numeric(15, 4), nullable=False)
    fill_date = Column(DateTime, nullable=False)

    # 수수료
    commission = Column(Numeric(15, 4), nullable=False, default=0)

    # 청산 정보
    exit_signal_price = Column(Numeric(15, 4), nullable=True)
    exit_fill_price = Column(Numeric(15, 4), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_commission = Column(Numeric(15, 4), nullable=True)

    # 손익
    pnl = Column(Numeric(15, 4), nullable=True)
    pnl_percent = Column(Numeric(10, 4), nullable=True)
    holding_days = Column(Integer, nullable=True)

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
    parameter_schema = Column(JSON, nullable=True)

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

    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "market",
            "timeframe",
            "timestamp",
            name="uq_market_data_identity",
        ),
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

    optimization_metric = Column(String(50), nullable=False)
    total_combinations = Column(Integer, nullable=False)
    parameter_ranges = Column(JSON, nullable=False)

    top_results = Column(JSON, nullable=True)

    job_status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_error = Column(String, nullable=True)
    progress = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class StrategyComparison(Base):
    """다중 전략 비교"""

    __tablename__ = "strategy_comparisons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)

    # 공통 설정
    market = Column(SAEnum(MarketType), nullable=False)
    symbols = Column(JSON, nullable=False)
    timeframe = Column(SAEnum(TimeframeType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)

    # 전략 목록: [{strategy_name, parameters}, ...]
    strategies = Column(JSON, nullable=False)

    # 생성된 백테스트 ID 목록
    backtest_ids = Column(JSON, nullable=False)

    # 작업 상태
    job_status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    job_error = Column(String, nullable=True)
    progress = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
