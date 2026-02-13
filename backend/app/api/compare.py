"""다중 전략 비교 API 엔드포인트"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import (
    CompareBacktestResult,
    CompareCreate,
    CompareResponse,
    JobResponse,
)
from app.db.models import Backtest, JobStatus, StrategyComparison
from app.db.session import get_db
from app.strategies import STRATEGY_REGISTRY
from app.utils.exceptions import (
    BacktestNotFoundError,
    InsufficientCapitalError,
    InvalidDateRangeError,
    StrategyNotFoundError,
)
from app.utils.response import success_response
from app.worker.tasks import run_backtest_task

router = APIRouter(prefix="/api/backtest/compare", tags=["compare"])


@router.post("")
def create_comparison(body: CompareCreate, db: Session = Depends(get_db)):
    """다중 전략 비교 작업 생성"""
    # 검증
    for item in body.strategies:
        if item.strategy_name not in STRATEGY_REGISTRY:
            raise StrategyNotFoundError(item.strategy_name)

    if body.start_date >= body.end_date:
        raise InvalidDateRangeError()

    min_capital = 100_000 if body.market.value == "KR" else 100
    if float(body.initial_capital) < min_capital:
        raise InsufficientCapitalError(
            f"최소 자본금: {min_capital} ({body.market.value})"
        )

    # 각 전략별 Backtest 레코드 생성 + Celery 태스크 발행
    backtest_ids = []
    for item in body.strategies:
        backtest = Backtest(
            name=f"[비교] {body.name} - {item.strategy_name}",
            description=f"전략 비교 '{body.name}'의 일부",
            strategy_name=item.strategy_name,
            parameters=item.parameters,
            market=body.market,
            symbols=body.symbols,
            timeframe=body.timeframe,
            start_date=body.start_date,
            end_date=body.end_date,
            initial_capital=body.initial_capital,
            job_status=JobStatus.PENDING,
        )
        db.add(backtest)
        db.flush()
        backtest_ids.append(backtest.id)

    # StrategyComparison 레코드 생성
    comparison = StrategyComparison(
        name=body.name,
        market=body.market,
        symbols=body.symbols,
        timeframe=body.timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        strategies=[s.model_dump() for s in body.strategies],
        backtest_ids=backtest_ids,
        job_status=JobStatus.RUNNING,
    )
    db.add(comparison)
    db.commit()

    # Celery 태스크 발행 (커밋 후)
    for bid in backtest_ids:
        run_backtest_task.delay(bid)

    return success_response(
        data=JobResponse(
            job_id=comparison.id,
            status=JobStatus.RUNNING,
            message=f"전략 비교 작업이 생성되었습니다 ({len(backtest_ids)}개 전략)",
        ).model_dump()
    )


@router.get("/{comparison_id}")
def get_comparison(comparison_id: str, db: Session = Depends(get_db)):
    """전략 비교 상세 조회"""
    comparison = (
        db.query(StrategyComparison)
        .filter(StrategyComparison.id == comparison_id)
        .first()
    )
    if not comparison:
        raise BacktestNotFoundError(comparison_id)

    # 각 백테스트 결과 수집
    backtests = (
        db.query(Backtest)
        .filter(Backtest.id.in_(comparison.backtest_ids))
        .all()
    )
    results = [CompareBacktestResult.model_validate(b).model_dump() for b in backtests]

    # 전체 상태 계산
    statuses = [b.job_status for b in backtests]
    if all(s == JobStatus.COMPLETED for s in statuses):
        overall_status = JobStatus.COMPLETED
        overall_progress = 100
    elif any(s == JobStatus.FAILED for s in statuses):
        overall_status = JobStatus.FAILED
        overall_progress = 0
    else:
        overall_status = JobStatus.RUNNING
        completed = sum(1 for s in statuses if s == JobStatus.COMPLETED)
        overall_progress = int(completed / len(statuses) * 100) if statuses else 0

    # 비교 레코드 상태 업데이트
    if comparison.job_status != overall_status:
        comparison.job_status = overall_status
        comparison.progress = overall_progress
        db.commit()

    resp = CompareResponse(
        id=comparison.id,
        name=comparison.name,
        market=comparison.market,
        symbols=comparison.symbols,
        timeframe=comparison.timeframe,
        start_date=comparison.start_date,
        end_date=comparison.end_date,
        initial_capital=comparison.initial_capital,
        strategies=comparison.strategies,
        job_status=overall_status,
        job_error=comparison.job_error,
        progress=overall_progress,
        results=results,
        created_at=comparison.created_at,
    )
    return success_response(data=resp.model_dump())


@router.get("/{comparison_id}/status")
def get_comparison_status(comparison_id: str, db: Session = Depends(get_db)):
    """전략 비교 작업 상태 폴링"""
    comparison = (
        db.query(StrategyComparison)
        .filter(StrategyComparison.id == comparison_id)
        .first()
    )
    if not comparison:
        raise BacktestNotFoundError(comparison_id)

    # 각 백테스트 상태 확인
    backtests = (
        db.query(Backtest)
        .filter(Backtest.id.in_(comparison.backtest_ids))
        .all()
    )
    statuses = [b.job_status for b in backtests]

    if all(s == JobStatus.COMPLETED for s in statuses):
        status = JobStatus.COMPLETED
        progress = 100
    elif any(s == JobStatus.FAILED for s in statuses):
        status = JobStatus.FAILED
        progress = 0
    else:
        status = JobStatus.RUNNING
        completed = sum(1 for s in statuses if s == JobStatus.COMPLETED)
        progress = int(completed / len(statuses) * 100) if statuses else 0

    if comparison.job_status != status:
        comparison.job_status = status
        comparison.progress = progress
        db.commit()

    return success_response(data={"status": status.value, "progress": progress})
