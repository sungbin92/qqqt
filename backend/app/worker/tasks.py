"""Celery 비동기 태스크 정의"""

import asyncio
import traceback
from datetime import datetime

import pandas as pd

from app.analytics.performance import PerformanceMetrics
from app.config import MARKET_CONFIGS
from app.data.cache import CachedDataProvider
from app.data.kis_api import KISDataProvider
from app.db.models import Backtest, JobStatus, Trade
from app.db.session import SessionLocal
from app.engine.backtest import BacktestEngine
from app.engine.broker import Broker
from app.strategies import get_strategy
from app.utils.logger import logger
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="run_backtest_task")
def run_backtest_task(self, backtest_id: str) -> dict:
    """백테스팅 비동기 실행 태스크"""
    db = SessionLocal()
    try:
        backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
        if not backtest:
            logger.error("Backtest not found: %s", backtest_id)
            return {"error": f"Backtest not found: {backtest_id}"}

        # RUNNING 상태로 업데이트
        backtest.job_status = JobStatus.RUNNING
        backtest.progress = 0
        db.commit()

        # 전략 인스턴스 생성
        strategy = get_strategy(backtest.strategy_name, backtest.parameters)

        # 데이터 수집
        kis_client = KISDataProvider()
        cached_provider = CachedDataProvider(kis_client, db)

        data = {}
        for symbol in backtest.symbols:
            df = asyncio.get_event_loop().run_until_complete(
                cached_provider.fetch_ohlcv(
                    symbol=symbol,
                    market=backtest.market,
                    timeframe=backtest.timeframe,
                    start=backtest.start_date,
                    end=backtest.end_date,
                )
            )
            if not df.empty:
                if "timestamp" in df.columns:
                    df = df.set_index("timestamp")
                data[symbol] = df

        if not data:
            backtest.job_status = JobStatus.FAILED
            backtest.job_error = "데이터를 수집할 수 없습니다"
            db.commit()
            return {"error": "No data collected"}

        # 엔진 실행
        broker = Broker(backtest.market.value, backtest.timeframe)

        def on_progress(pct: int):
            backtest.progress = pct
            db.commit()

        engine = BacktestEngine(
            strategy=strategy,
            data=data,
            broker=broker,
            initial_capital=float(backtest.initial_capital),
            on_progress=on_progress,
        )

        result = engine.run()

        # 성과 지표 계산
        equity_curve_df = result["equity_curve"]
        if not equity_curve_df.empty:
            equity_series = equity_curve_df["equity"]
            market_config = MARKET_CONFIGS[backtest.market.value]
            trading_days = market_config.trading_days_per_year

            backtest.total_return = float(PerformanceMetrics.total_return(equity_series))
            backtest.annual_return = float(
                PerformanceMetrics.annual_return(equity_series, trading_days)
            )
            backtest.sharpe_ratio = float(
                PerformanceMetrics.sharpe_ratio(equity_series, trading_days=trading_days)
            )
            backtest.sortino_ratio = float(
                PerformanceMetrics.sortino_ratio(equity_series, trading_days=trading_days)
            )
            backtest.max_drawdown = float(PerformanceMetrics.max_drawdown(equity_series))

            # equity_curve_data JSON 저장
            curve_data = []
            for _, row in equity_curve_df.iterrows():
                ts = row["timestamp"]
                if hasattr(ts, "isoformat"):
                    ts_str = ts.isoformat()
                else:
                    ts_str = str(ts)
                curve_data.append(
                    {
                        "timestamp": ts_str,
                        "equity": float(row["equity"]),
                        "cash": float(row["cash"]),
                    }
                )
            backtest.equity_curve_data = curve_data

        # trades → Trade 레코드 저장 및 매매 지표 계산
        engine_trades = result["trades"]
        _save_trades(db, backtest, engine_trades)

        # 매매 기반 지표 계산
        trade_records = db.query(Trade).filter(Trade.backtest_id == backtest_id).all()
        _calculate_trade_metrics(backtest, trade_records)

        backtest.job_status = JobStatus.COMPLETED
        backtest.progress = 100
        db.commit()

        logger.info("백테스트 완료: %s", backtest_id)
        return {"status": "COMPLETED", "backtest_id": backtest_id}

    except Exception as e:
        logger.error("백테스트 실패: %s — %s", backtest_id, traceback.format_exc())
        try:
            backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
            if backtest:
                backtest.job_status = JobStatus.FAILED
                backtest.job_error = str(e)
                db.commit()
        except Exception:
            db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def _to_python_datetime(val):
    """pandas Timestamp / numpy datetime64 → Python datetime"""
    if val is None:
        return None
    if hasattr(val, "to_pydatetime"):
        return val.to_pydatetime()
    return val


def _save_trades(db, backtest: Backtest, engine_trades: list) -> None:
    """엔진 trades를 DB Trade 레코드로 변환·저장"""
    from app.engine.order import OrderSide as EngineOrderSide

    # BUY/SELL 쌍을 매칭하여 청산 정보도 기록
    open_positions: dict = {}  # symbol → Trade DB record

    for filled in engine_trades:
        if filled.side == EngineOrderSide.BUY:
            trade = Trade(
                backtest_id=backtest.id,
                symbol=filled.symbol,
                side="BUY",
                quantity=int(filled.quantity),
                signal_price=float(filled.signal_price),
                signal_date=_to_python_datetime(filled.signal_date),
                fill_price=float(filled.fill_price),
                fill_date=_to_python_datetime(filled.fill_date),
                commission=float(filled.commission),
            )
            db.add(trade)
            db.flush()
            open_positions[filled.symbol] = trade

        elif filled.side == EngineOrderSide.SELL:
            buy_trade = open_positions.pop(filled.symbol, None)
            if buy_trade:
                buy_trade.exit_signal_price = float(filled.signal_price)
                buy_trade.exit_fill_price = float(filled.fill_price)
                buy_trade.exit_date = _to_python_datetime(filled.fill_date)
                buy_trade.exit_commission = float(filled.commission)
                # PnL 계산
                buy_cost = float(buy_trade.fill_price) * buy_trade.quantity + float(
                    buy_trade.commission
                )
                sell_revenue = (
                    float(filled.fill_price) * filled.quantity - float(filled.commission)
                )
                buy_trade.pnl = float(sell_revenue - buy_cost)
                buy_trade.pnl_percent = float(buy_trade.pnl / buy_cost) if buy_cost > 0 else 0.0
                # 보유일수
                if buy_trade.fill_date and filled.fill_date:
                    delta = _to_python_datetime(filled.fill_date) - buy_trade.fill_date
                    buy_trade.holding_days = delta.days
            else:
                # 매수 없이 매도만 있는 경우 (비정상)
                trade = Trade(
                    backtest_id=backtest.id,
                    symbol=filled.symbol,
                    side="SELL",
                    quantity=int(filled.quantity),
                    signal_price=float(filled.signal_price),
                    signal_date=_to_python_datetime(filled.signal_date),
                    fill_price=float(filled.fill_price),
                    fill_date=_to_python_datetime(filled.fill_date),
                    commission=float(filled.commission),
                )
                db.add(trade)

    db.flush()


def _calculate_trade_metrics(backtest: Backtest, trade_records: list) -> None:
    """완료된 거래들로 매매 지표 계산"""
    closed = [t for t in trade_records if t.pnl is not None]
    backtest.total_trades = len(closed)

    if not closed:
        return

    pnls = pd.DataFrame([{"pnl": float(t.pnl)} for t in closed])
    backtest.win_rate = float(PerformanceMetrics.win_rate(pnls))
    backtest.profit_factor = float(PerformanceMetrics.profit_factor(pnls))
    backtest.max_consecutive_wins = int(PerformanceMetrics.max_consecutive(pnls, win=True))
    backtest.max_consecutive_losses = int(PerformanceMetrics.max_consecutive(pnls, win=False))

    wins = [float(t.pnl) for t in closed if float(t.pnl) > 0]
    losses = [float(t.pnl) for t in closed if float(t.pnl) <= 0]
    backtest.avg_win = sum(wins) / len(wins) if wins else None
    backtest.avg_loss = sum(losses) / len(losses) if losses else None


@celery_app.task(bind=True, name="run_optimization_task")
def run_optimization_task(self, optimization_id: str) -> dict:
    """파라미터 최적화 태스크"""
    from app.db.models import OptimizationResult
    from app.optimizer.grid_search import generate_combinations, run_grid_search

    db = SessionLocal()
    try:
        opt = db.query(OptimizationResult).filter(OptimizationResult.id == optimization_id).first()
        if not opt:
            logger.error("Optimization not found: %s", optimization_id)
            return {"error": f"Optimization not found: {optimization_id}"}

        # RUNNING 상태로 업데이트
        opt.job_status = JobStatus.RUNNING
        opt.progress = 0
        db.commit()

        # 데이터 수집 (run_backtest_task와 동일 패턴)
        kis_client = KISDataProvider()
        cached_provider = CachedDataProvider(kis_client, db)

        data = {}
        for symbol in opt.symbols:
            df = asyncio.get_event_loop().run_until_complete(
                cached_provider.fetch_ohlcv(
                    symbol=symbol,
                    market=opt.market,
                    timeframe=opt.timeframe,
                    start=opt.start_date,
                    end=opt.end_date,
                )
            )
            if not df.empty:
                if "timestamp" in df.columns:
                    df = df.set_index("timestamp")
                data[symbol] = df

        if not data:
            opt.job_status = JobStatus.FAILED
            opt.job_error = "데이터를 수집할 수 없습니다"
            db.commit()
            return {"error": "No data collected"}

        # 조합 생성 및 Grid Search 실행
        combinations = generate_combinations(opt.parameter_ranges)

        def on_progress(pct: int):
            opt.progress = pct
            db.commit()

        top_results = run_grid_search(
            strategy_name=opt.strategy_name,
            combinations=combinations,
            data=data,
            market=opt.market.value,
            timeframe=opt.timeframe,
            initial_capital=float(opt.initial_capital),
            optimization_metric=opt.optimization_metric,
            on_progress=on_progress,
        )

        # 결과 저장 (float 변환으로 JSON 직렬화 보장)
        serializable_results = []
        for r in top_results:
            item = {"parameters": r["parameters"]}
            for key in ["total_return", "annual_return", "sharpe_ratio", "sortino_ratio",
                        "max_drawdown", "total_trades", "final_equity"]:
                val = r.get(key)
                item[key] = float(val) if val is not None else None
            serializable_results.append(item)

        opt.top_results = serializable_results
        opt.job_status = JobStatus.COMPLETED
        opt.progress = 100
        db.commit()

        logger.info("최적화 완료: %s", optimization_id)
        return {"status": "COMPLETED", "optimization_id": optimization_id}

    except Exception as e:
        logger.error("최적화 실패: %s — %s", optimization_id, traceback.format_exc())
        try:
            opt = (
                db.query(OptimizationResult)
                .filter(OptimizationResult.id == optimization_id)
                .first()
            )
            if opt:
                opt.job_status = JobStatus.FAILED
                opt.job_error = str(e)
                db.commit()
        except Exception:
            db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
