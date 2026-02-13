"""백테스팅 API 엔드포인트"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import BacktestCreate, BacktestDetail, BacktestSummary, JobResponse
from app.db.models import Backtest, JobStatus
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

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("")
def create_backtest(body: BacktestCreate, db: Session = Depends(get_db)):
    """백테스팅 작업 생성"""
    # 검증
    if body.strategy_name not in STRATEGY_REGISTRY:
        raise StrategyNotFoundError(body.strategy_name)

    if body.start_date >= body.end_date:
        raise InvalidDateRangeError()

    min_capital = 100_000 if body.market.value == "KR" else 100
    if float(body.initial_capital) < min_capital:
        raise InsufficientCapitalError(
            f"최소 자본금: {min_capital} ({body.market.value})"
        )

    # DB 레코드 생성
    backtest = Backtest(
        name=body.name,
        description=body.description,
        strategy_name=body.strategy_name,
        parameters=body.parameters,
        market=body.market,
        symbols=body.symbols,
        timeframe=body.timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        job_status=JobStatus.PENDING,
    )
    db.add(backtest)
    db.commit()
    db.refresh(backtest)

    # Celery 태스크 발행
    run_backtest_task.delay(backtest.id)

    return success_response(
        data=JobResponse(
            job_id=backtest.id,
            status=JobStatus.PENDING,
            message="백테스팅 작업이 생성되었습니다",
        ).model_dump()
    )


@router.get("")
def list_backtests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """백테스팅 목록 조회"""
    offset = (page - 1) * limit
    total = db.query(Backtest).count()
    backtests = (
        db.query(Backtest)
        .order_by(Backtest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [BacktestSummary.model_validate(b).model_dump() for b in backtests]

    return success_response(
        data=items,
        meta={"page": page, "limit": limit, "total": total},
    )


@router.get("/{backtest_id}")
def get_backtest(backtest_id: str, db: Session = Depends(get_db)):
    """백테스팅 상세 조회"""
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise BacktestNotFoundError(backtest_id)

    detail = BacktestDetail.model_validate(backtest)
    return success_response(data=detail.model_dump())


@router.get("/{backtest_id}/status")
def get_backtest_status(backtest_id: str, db: Session = Depends(get_db)):
    """백테스팅 작업 상태 폴링"""
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise BacktestNotFoundError(backtest_id)

    return success_response(
        data={"status": backtest.job_status.value, "progress": backtest.progress}
    )


@router.delete("/{backtest_id}")
def delete_backtest(backtest_id: str, db: Session = Depends(get_db)):
    """백테스팅 삭제"""
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise BacktestNotFoundError(backtest_id)

    db.delete(backtest)
    db.commit()
    return success_response(data={"message": "삭제되었습니다"})


@router.get("/{backtest_id}/export")
def export_backtest_csv(backtest_id: str, db: Session = Depends(get_db)):
    """백테스팅 결과 CSV 다운로드"""
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise BacktestNotFoundError(backtest_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더
    writer.writerow(
        [
            "symbol",
            "side",
            "quantity",
            "signal_price",
            "signal_date",
            "fill_price",
            "fill_date",
            "commission",
            "exit_fill_price",
            "exit_date",
            "exit_commission",
            "pnl",
            "pnl_percent",
            "holding_days",
        ]
    )

    for trade in backtest.trades:
        writer.writerow(
            [
                trade.symbol,
                trade.side.value if hasattr(trade.side, "value") else trade.side,
                trade.quantity,
                trade.signal_price,
                trade.signal_date,
                trade.fill_price,
                trade.fill_date,
                trade.commission,
                trade.exit_fill_price,
                trade.exit_date,
                trade.exit_commission,
                trade.pnl,
                trade.pnl_percent,
                trade.holding_days,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}.csv"},
    )
