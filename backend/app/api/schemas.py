from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.db.models import JobStatus, MarketType, TimeframeType


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
    total_return: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    total_trades: int
    created_at: datetime

    model_config = {"from_attributes": True}


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
    exit_fill_price: Optional[Decimal] = None
    exit_date: Optional[datetime] = None
    exit_commission: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    holding_days: Optional[int] = None

    model_config = {"from_attributes": True}


class BacktestDetail(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    strategy_name: str
    parameters: Dict[str, Any]
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal

    job_status: JobStatus
    job_error: Optional[str] = None
    progress: int

    total_return: Optional[Decimal] = None
    annual_return: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    total_trades: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_win: Optional[Decimal] = None
    avg_loss: Optional[Decimal] = None

    equity_curve_data: Optional[List[Dict[str, Any]]] = None
    trades: List[TradeResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 최적화 ──


class OptimizeCreate(BaseModel):
    strategy_name: str
    parameter_ranges: Dict[str, Dict[str, float]]
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    optimization_metric: str = "sharpe_ratio"


class OptimizationResponse(BaseModel):
    id: str
    strategy_name: str
    parameter_ranges: Dict[str, Dict[str, float]]
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    optimization_metric: str
    total_combinations: int

    job_status: JobStatus
    job_error: Optional[str] = None
    progress: int = 0

    top_results: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 비동기 작업 ──


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


# ── 전략 템플릿 ──


# ── 다중 전략 비교 ──


class StrategyCompareItem(BaseModel):
    strategy_name: str
    parameters: Dict[str, Any]


class CompareCreate(BaseModel):
    name: str = Field(..., max_length=200)
    strategies: List[StrategyCompareItem] = Field(..., min_length=2, max_length=10)
    market: MarketType
    symbols: List[str] = Field(..., min_length=1, max_length=100)
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Field(..., gt=0)


class CompareBacktestResult(BaseModel):
    """비교 내 개별 백테스트 요약"""

    id: str
    strategy_name: str
    parameters: Dict[str, Any]
    job_status: JobStatus
    total_return: Optional[Decimal] = None
    annual_return: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    total_trades: int = 0
    equity_curve_data: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}


class CompareResponse(BaseModel):
    id: str
    name: str
    market: MarketType
    symbols: List[str]
    timeframe: TimeframeType
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    strategies: List[Dict[str, Any]]
    job_status: JobStatus
    job_error: Optional[str] = None
    progress: int = 0
    results: List[CompareBacktestResult] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 전략 템플릿 ──


class StrategyTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    strategy_type: str
    default_parameters: Dict[str, Any]
    parameter_schema: Optional[Dict[str, Any]] = None


class StrategyTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    strategy_type: str
    default_parameters: Dict[str, Any]
    parameter_schema: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
