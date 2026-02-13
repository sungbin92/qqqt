"""파라미터 최적화 API 엔드포인트"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import JobResponse, OptimizationResponse, OptimizeCreate
from app.db.models import JobStatus, OptimizationResult
from app.db.session import get_db
from app.optimizer.grid_search import count_combinations
from app.strategies import STRATEGY_REGISTRY
from app.utils.exceptions import BacktestNotFoundError, StrategyNotFoundError, TooManyCombinationsError
from app.utils.response import success_response
from app.worker.tasks import run_optimization_task

router = APIRouter(prefix="/api/optimize", tags=["optimize"])


@router.post("")
def create_optimization(body: OptimizeCreate, db: Session = Depends(get_db)):
    """최적화 작업 생성"""
    # 전략 존재 검증
    if body.strategy_name not in STRATEGY_REGISTRY:
        raise StrategyNotFoundError(body.strategy_name)

    # 조합 수 검증
    total = count_combinations(body.parameter_ranges)
    if total > 10_000:
        raise TooManyCombinationsError(
            f"조합 수 {total:,}개가 최대 허용 10,000개를 초과합니다"
        )

    # DB 레코드 생성
    opt = OptimizationResult(
        strategy_name=body.strategy_name,
        parameter_ranges=body.parameter_ranges,
        market=body.market,
        symbols=body.symbols,
        timeframe=body.timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        optimization_metric=body.optimization_metric,
        total_combinations=total,
        job_status=JobStatus.PENDING,
    )
    db.add(opt)
    db.commit()
    db.refresh(opt)

    # Celery 태스크 발행
    run_optimization_task.delay(opt.id)

    return success_response(
        data=JobResponse(
            job_id=opt.id,
            status=JobStatus.PENDING,
            message=f"최적화 작업이 생성되었습니다 (조합 수: {total:,})",
        ).model_dump()
    )


@router.get("/{optimization_id}")
def get_optimization(optimization_id: str, db: Session = Depends(get_db)):
    """최적화 결과 상세 조회"""
    opt = db.query(OptimizationResult).filter(OptimizationResult.id == optimization_id).first()
    if not opt:
        raise BacktestNotFoundError(optimization_id)

    detail = OptimizationResponse.model_validate(opt)
    return success_response(data=detail.model_dump())


@router.get("/{optimization_id}/status")
def get_optimization_status(optimization_id: str, db: Session = Depends(get_db)):
    """최적화 작업 상태 폴링"""
    opt = db.query(OptimizationResult).filter(OptimizationResult.id == optimization_id).first()
    if not opt:
        raise BacktestNotFoundError(optimization_id)

    return success_response(
        data={"status": opt.job_status.value, "progress": opt.progress}
    )
