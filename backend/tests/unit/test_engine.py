from typing import Dict, List

import pandas as pd
import pytest

from app.db.models import TimeframeType
from app.engine.backtest import BacktestEngine
from app.engine.broker import Broker
from app.engine.order import OrderSide, PendingOrder
from app.engine.portfolio import Portfolio
from app.strategies.base import Strategy


# ──────────────────────────────────────────────
# 테스트용 전략
# ──────────────────────────────────────────────


class BuyEveryBarStrategy(Strategy):
    """매 봉마다 30% 비중으로 매수하는 단순 전략"""

    def on_bar(self, bars: Dict[str, pd.Series], portfolio: Portfolio) -> List[PendingOrder]:
        orders = []
        for symbol in bars:
            if portfolio.get_position(symbol) is None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=0.3,
                        reason="매봉 매수",
                    )
                )
        return orders


class BuyThenSellStrategy(Strategy):
    """첫 봉에 매수, 포지션이 있으면 매도"""

    def on_bar(self, bars: Dict[str, pd.Series], portfolio: Portfolio) -> List[PendingOrder]:
        orders = []
        for symbol in bars:
            pos = portfolio.get_position(symbol)
            if pos is None:
                orders.append(
                    PendingOrder(symbol=symbol, side=OrderSide.BUY, weight=0.3)
                )
            else:
                orders.append(
                    PendingOrder(symbol=symbol, side=OrderSide.SELL, weight=1.0)
                )
        return orders


class NoOpStrategy(Strategy):
    """아무 주문도 생성하지 않는 전략"""

    def on_bar(self, bars: Dict[str, pd.Series], portfolio: Portfolio) -> List[PendingOrder]:
        return []


# ──────────────────────────────────────────────
# 테스트용 OHLCV 데이터 생성 헬퍼
# ──────────────────────────────────────────────


def make_ohlcv(prices: list, symbol: str = "005930") -> Dict[str, pd.DataFrame]:
    """
    가격 리스트로 간단한 OHLCV DataFrame 생성.
    각 항목은 (open, high, low, close, volume) 또는 단일 float(모든 가격 동일).
    """
    rows = []
    for i, p in enumerate(prices):
        if isinstance(p, (int, float)):
            rows.append(
                {
                    "open": float(p),
                    "high": float(p),
                    "low": float(p),
                    "close": float(p),
                    "volume": 1000,
                }
            )
        else:
            o, h, l, c, v = p
            rows.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
    df = pd.DataFrame(rows)
    df.index = pd.date_range("2024-01-01", periods=len(rows), freq="D")
    return {symbol: df}


# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────


class TestBacktestEngineBasic:
    """기본 엔진 동작 검증"""

    def test_buy_every_bar_strategy(self):
        """매봉 매수 전략 → 첫 매수가 t+1봉에서 체결"""
        data = make_ohlcv([70_000, 71_000, 72_000, 73_000, 74_000])
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=BuyEveryBarStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()

        # 첫 봉(t=0)에서 시그널 → 두 번째 봉(t=1)에서 체결
        assert len(result["trades"]) >= 1
        first_trade = result["trades"][0]
        assert first_trade.side == OrderSide.BUY
        assert first_trade.symbol == "005930"
        # 체결가는 t=1 봉의 시가(71,000) + 슬리피지
        expected_fill = 71_000 * (1 + 0.001)  # KR daily slippage
        assert first_trade.fill_price == pytest.approx(expected_fill)

    def test_signal_fill_timing(self):
        """시그널(t봉 종가) → 체결(t+1봉 시가) 타이밍 검증"""
        data = make_ohlcv(
            [
                (70_000, 72_000, 69_000, 71_000, 1000),  # t=0
                (71_500, 73_000, 71_000, 72_000, 1000),  # t=1: 체결
                (72_500, 74_000, 72_000, 73_000, 1000),  # t=2
            ]
        )
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=BuyEveryBarStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()

        assert len(result["trades"]) >= 1
        trade = result["trades"][0]
        # signal_price = t=0의 close = 71,000
        assert trade.signal_price == pytest.approx(71_000)
        # fill_price = t=1의 open(71,500) × (1 + 0.001)
        assert trade.fill_price == pytest.approx(71_500 * 1.001)

    def test_commission_slippage_in_pnl(self):
        """수수료/슬리피지가 반영된 PnL 검증"""
        data = make_ohlcv([70_000, 71_000, 72_000])
        broker = Broker("KR", TimeframeType.D1)
        initial = 10_000_000
        engine = BacktestEngine(
            strategy=BuyThenSellStrategy({}),
            data=data,
            broker=broker,
            initial_capital=initial,
        )
        result = engine.run()

        # 매수 + 매도 = 2 거래
        assert len(result["trades"]) == 2
        buy_trade = result["trades"][0]
        sell_trade = result["trades"][1]

        assert buy_trade.side == OrderSide.BUY
        assert sell_trade.side == OrderSide.SELL

        # 수수료가 0보다 큰지 확인
        assert buy_trade.commission > 0
        assert sell_trade.commission > 0

        # 최종 equity는 초기 자본과 다를 것 (수수료/슬리피지 반영)
        assert result["final_equity"] != initial


class TestBacktestEngineEdgeCases:
    """엣지 케이스"""

    def test_less_than_two_bars(self):
        """데이터 1봉: 백테스트 실행 불가"""
        data = make_ohlcv([70_000])
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=BuyEveryBarStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()

        assert len(result["trades"]) == 0
        assert result["final_equity"] == 10_000_000

    def test_empty_data(self):
        """빈 데이터"""
        data = {"005930": pd.DataFrame(columns=["open", "high", "low", "close", "volume"])}
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=BuyEveryBarStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()

        assert len(result["trades"]) == 0
        assert result["final_equity"] == 10_000_000

    def test_no_op_strategy(self):
        """주문 없는 전략: 거래 없이 equity 유지"""
        data = make_ohlcv([70_000, 71_000, 72_000])
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=NoOpStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()

        assert len(result["trades"]) == 0
        assert result["final_equity"] == 10_000_000


class TestBacktestEngineEquityCurve:
    """equity_curve 검증"""

    def test_equity_curve_recorded(self):
        """equity_curve가 각 봉마다 기록되는지 확인"""
        data = make_ohlcv([70_000, 71_000, 72_000, 73_000])
        broker = Broker("KR", TimeframeType.D1)
        engine = BacktestEngine(
            strategy=NoOpStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
        )
        result = engine.run()
        ec = result["equity_curve"]

        assert len(ec) == 4
        assert "timestamp" in ec.columns
        assert "equity" in ec.columns
        assert "cash" in ec.columns


class TestBacktestEngineProgress:
    """진행률 콜백 테스트"""

    def test_progress_callback(self):
        """on_progress 콜백 호출 확인"""
        data = make_ohlcv([70_000, 71_000, 72_000, 73_000, 74_000])
        broker = Broker("KR", TimeframeType.D1)
        progress_values = []

        engine = BacktestEngine(
            strategy=NoOpStrategy({}),
            data=data,
            broker=broker,
            initial_capital=10_000_000,
            on_progress=lambda pct: progress_values.append(pct),
        )
        engine.run()

        # 마지막은 100이어야 함
        assert progress_values[-1] == 100
        # 증가하는 순서
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]
