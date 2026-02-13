import math
import os

import numpy as np
import pandas as pd
import pytest

from app.analytics.performance import PerformanceMetrics
from app.analytics.risk import RiskMetrics
from app.db.models import TimeframeType
from app.engine.backtest import BacktestEngine
from app.engine.broker import Broker
from app.engine.order import OrderSide
from app.strategies.mean_reversion import MeanReversionStrategy


@pytest.fixture
def sample_df():
    """sample_ohlcv.csv → DatetimeIndex DataFrame"""
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "sample_ohlcv.csv"
    )
    df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
    return df


@pytest.fixture
def kr_broker():
    return Broker(market="KR", timeframe=TimeframeType.D1)


@pytest.fixture
def us_broker():
    return Broker(market="US", timeframe=TimeframeType.D1)


@pytest.fixture
def strategy():
    return MeanReversionStrategy()


def run_backtest(strategy, data, broker, initial_capital=100_000_000):
    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        broker=broker,
        initial_capital=initial_capital,
    )
    return engine.run(), engine


class TestE2EKoreanMarket:
    """KR 시장 E2E 백테스트"""

    def test_backtest_runs_without_error(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        assert "trades" in result
        assert "equity_curve" in result
        assert "final_equity" in result

    def test_trades_not_empty(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        assert len(result["trades"]) > 0, "60봉 데이터로 최소 1건의 거래가 발생해야 함"

    def test_fill_date_after_signal_date(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        for trade in result["trades"]:
            assert trade.fill_date > trade.signal_date, (
                f"fill_date({trade.fill_date})가 signal_date({trade.signal_date})보다 이후여야 함"
            )

    def test_equity_curve_length(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        eq_df = result["equity_curve"]
        assert len(eq_df) == len(sample_df), (
            f"equity_curve 길이({len(eq_df)})가 데이터 봉 수({len(sample_df)})와 같아야 함"
        )

    def test_performance_metrics_not_nan(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        eq_series = result["equity_curve"]["equity"]

        total_ret = PerformanceMetrics.total_return(eq_series)
        ann_ret = PerformanceMetrics.annual_return(eq_series)
        sharpe = PerformanceMetrics.sharpe_ratio(eq_series)
        mdd = PerformanceMetrics.max_drawdown(eq_series)

        assert not math.isnan(total_ret), "total_return이 NaN"
        assert not math.isnan(ann_ret), "annual_return이 NaN"
        assert not math.isnan(sharpe), "sharpe_ratio가 NaN"
        assert not math.isnan(mdd), "max_drawdown이 NaN"

        assert total_ret is not None
        assert ann_ret is not None
        assert sharpe is not None
        assert mdd is not None

    def test_trade_metrics_not_nan(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        trades = result["trades"]

        # trades를 DataFrame으로 변환하여 pnl 계산
        if len(trades) >= 2:
            # 매수-매도 쌍으로 pnl 계산
            trade_records = []
            for t in trades:
                trade_records.append(
                    {
                        "symbol": t.symbol,
                        "side": t.side.value,
                        "fill_price": t.fill_price,
                        "quantity": t.quantity,
                        "commission": t.commission,
                    }
                )
            trade_df = pd.DataFrame(trade_records)

            # 간단 pnl: 매도가*수량 - 매수가*수량 - 수수료 합계
            buys = trade_df[trade_df["side"] == "BUY"]
            sells = trade_df[trade_df["side"] == "SELL"]

            if len(sells) > 0:
                # pnl 컬럼을 만들어 win_rate 등 테스트
                pnl_list = []
                for _, sell in sells.iterrows():
                    matching_buy = buys[buys["symbol"] == sell["symbol"]].iloc[0]
                    pnl = (
                        sell["fill_price"] * sell["quantity"]
                        - matching_buy["fill_price"] * matching_buy["quantity"]
                        - sell["commission"]
                        - matching_buy["commission"]
                    )
                    pnl_list.append(pnl)

                pnl_df = pd.DataFrame({"pnl": pnl_list})
                wr = PerformanceMetrics.win_rate(pnl_df)
                pf = PerformanceMetrics.profit_factor(pnl_df)
                assert not math.isnan(wr)
                assert not math.isnan(pf)

    def test_portfolio_equity_consistency(self, strategy, sample_df, kr_broker):
        """최종 equity == portfolio.equity (정합성)"""
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        assert pytest.approx(result["final_equity"], rel=1e-6) == engine.portfolio.equity

    def test_risk_metrics(self, strategy, sample_df, kr_broker):
        result, engine = run_backtest(strategy, {"005930": sample_df}, kr_broker)
        eq_series = result["equity_curve"]["equity"]

        calmar = RiskMetrics.calmar_ratio(eq_series)
        var = RiskMetrics.value_at_risk(eq_series)

        assert not math.isnan(calmar)
        assert not math.isnan(var)


class TestE2EUSMarket:
    """US 시장 설정으로 동일 테스트 (수수료 체계 변경 확인)"""

    def test_backtest_runs_with_us_market(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        assert "trades" in result
        assert "equity_curve" in result

    def test_trades_not_empty_us(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        assert len(result["trades"]) > 0

    def test_fill_date_after_signal_date_us(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        for trade in result["trades"]:
            assert trade.fill_date > trade.signal_date

    def test_equity_curve_length_us(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        assert len(result["equity_curve"]) == len(sample_df)

    def test_performance_metrics_us(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        eq_series = result["equity_curve"]["equity"]

        total_ret = PerformanceMetrics.total_return(eq_series)
        sharpe = PerformanceMetrics.sharpe_ratio(eq_series)
        mdd = PerformanceMetrics.max_drawdown(eq_series)

        assert not math.isnan(total_ret)
        assert not math.isnan(sharpe)
        assert not math.isnan(mdd)

    def test_us_commission_differs_from_kr(self, kr_broker, us_broker):
        """US와 KR의 수수료 체계가 다른지 확인"""
        kr_comm = kr_broker.calculate_commission(70000, 100)
        us_comm = us_broker.calculate_commission(70000, 100)
        # 수수료율이 다르므로 수수료 금액도 달라야 함
        assert kr_comm != us_comm

    def test_portfolio_equity_consistency_us(self, strategy, sample_df, us_broker):
        result, engine = run_backtest(
            strategy, {"AAPL": sample_df}, us_broker, initial_capital=1_000_000
        )
        assert pytest.approx(result["final_equity"], rel=1e-6) == engine.portfolio.equity
