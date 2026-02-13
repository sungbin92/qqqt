from typing import Callable, Dict, List, Optional

import pandas as pd

from app.engine.broker import Broker
from app.engine.order import FilledOrder, OrderSide, PendingOrder
from app.engine.portfolio import Portfolio
from app.strategies.base import Strategy
from app.utils.logger import logger


class BacktestEngine:
    """
    백테스팅 엔진.

    메인 루프:
      1. 봉(t) 완성 → strategy.on_bar() → PendingOrder 수집
      2. 다음 봉(t+1) 도착 → Broker가 체결가 결정 → 주문 실행
      3. equity_curve 기록
    """

    def __init__(
        self,
        strategy: Strategy,
        data: Dict[str, pd.DataFrame],
        broker: Broker,
        initial_capital: float,
        on_progress: Optional[Callable[[int], None]] = None,
    ):
        """
        Args:
            strategy: 전략 인스턴스
            data: {symbol: OHLCV DataFrame} (columns: open, high, low, close, volume)
            broker: Broker 인스턴스
            initial_capital: 초기 자본금
            on_progress: 진행률 콜백 (0~100)
        """
        self.strategy = strategy
        self.data = data
        self.broker = broker
        self.portfolio = Portfolio(initial_capital)
        self.on_progress = on_progress

        self.trades: List[FilledOrder] = []
        self.equity_curve: List[Dict] = []

    def run(self) -> Dict:
        """
        백테스트 실행.

        Returns:
            {"trades": [...], "equity_curve": DataFrame, "final_equity": float}
        """
        # 공통 인덱스 구하기 (모든 종목에 존재하는 날짜)
        indices = None
        for df in self.data.values():
            idx = df.index
            indices = idx if indices is None else indices.intersection(idx)

        if indices is None or len(indices) < 2:
            logger.warning("데이터가 2봉 미만이어서 백테스트를 실행할 수 없습니다.")
            return {
                "trades": [],
                "equity_curve": pd.DataFrame(),
                "final_equity": self.portfolio.equity,
            }

        indices = indices.sort_values()
        total_bars = len(indices)
        pending_orders: List[PendingOrder] = []

        for i, current_time in enumerate(indices):
            # 1) 이전 봉에서 발생한 주문을 현재 봉의 시가로 체결
            if pending_orders:
                self._fill_orders(pending_orders, current_time)
                pending_orders = []

            # 2) 시가평가 갱신 (현재 봉의 종가)
            prices = {}
            bars = {}
            for symbol, df in self.data.items():
                if current_time in df.index:
                    row = df.loc[current_time]
                    prices[symbol] = row["close"]
                    bars[symbol] = row
            self.portfolio.update_market_prices(prices)

            # 3) equity_curve 기록
            self.equity_curve.append(
                {
                    "timestamp": current_time,
                    "equity": self.portfolio.equity,
                    "cash": self.portfolio.cash,
                }
            )

            # 4) 마지막 봉이면 새 주문 생성하지 않음 (체결할 다음 봉 없음)
            if i >= total_bars - 1:
                break

            # 5) 전략 호출 → PendingOrder 수집
            pending_orders = self.strategy.on_bar(bars, self.portfolio)

            # 6) 진행률 콜백
            if self.on_progress:
                pct = int((i + 1) / total_bars * 100)
                self.on_progress(pct)

        if self.on_progress:
            self.on_progress(100)

        return {
            "trades": self.trades,
            "equity_curve": pd.DataFrame(self.equity_curve),
            "final_equity": self.portfolio.equity,
        }

    def _fill_orders(self, orders: List[PendingOrder], current_time) -> None:
        """주문 체결 처리 (현재 봉의 시가 기준)"""
        for order in orders:
            df = self.data.get(order.symbol)
            if df is None or current_time not in df.index:
                logger.warning(f"종목 {order.symbol}의 데이터가 없어 주문 취소")
                continue

            row = df.loc[current_time]
            next_open = row["open"]

            # 매도: 포지션 없으면 스킵
            if order.side == OrderSide.SELL:
                pos = self.portfolio.get_position(order.symbol)
                if pos is None:
                    logger.warning(f"{order.symbol} 포지션 없음 → 매도 주문 취소")
                    continue

            # 체결가 결정
            fill_price = self.broker.calculate_fill_price(next_open, order.side.value)

            if order.side == OrderSide.BUY:
                self._fill_buy(order, fill_price, current_time)
            else:
                self._fill_sell(order, fill_price, current_time)

    def _fill_buy(self, order: PendingOrder, fill_price: float, fill_time) -> None:
        """매수 주문 체결"""
        pos = self.portfolio.get_position(order.symbol)
        current_value = pos.market_value if pos else 0

        quantity = self.broker.calculate_quantity(
            self.portfolio.equity, order.weight, fill_price, current_value
        )
        if quantity == 0:
            logger.info(f"{order.symbol} 매수 수량 0 → 주문 취소")
            return

        valid, reason = self.broker.validate_order(
            self.portfolio.equity, self.portfolio.cash, fill_price, quantity
        )
        if not valid:
            logger.info(f"{order.symbol} 매수 주문 거부: {reason}")
            return

        commission = self.broker.calculate_commission(fill_price, quantity)
        self.portfolio.execute_buy(order.symbol, quantity, fill_price, commission)

        # 시그널 가격: 이전 봉의 종가 (주문 생성 시점)
        signal_price = self._get_prev_close(order.symbol, fill_time)

        filled = FilledOrder(
            symbol=order.symbol,
            side=OrderSide.BUY,
            signal_price=signal_price,
            signal_date=self._get_prev_time(fill_time),
            fill_price=fill_price,
            fill_date=fill_time,
            quantity=quantity,
            commission=commission,
        )
        self.trades.append(filled)
        logger.info(
            f"매수 체결: {order.symbol} {quantity}주 @ {fill_price:.2f} "
            f"(수수료: {commission:.2f})"
        )

    def _fill_sell(self, order: PendingOrder, fill_price: float, fill_time) -> None:
        """매도 주문 체결"""
        pos = self.portfolio.get_position(order.symbol)
        quantity = pos.quantity  # 전량 매도

        commission = self.broker.calculate_commission(fill_price, quantity)
        self.portfolio.execute_sell(order.symbol, quantity, fill_price, commission)

        signal_price = self._get_prev_close(order.symbol, fill_time)

        filled = FilledOrder(
            symbol=order.symbol,
            side=OrderSide.SELL,
            signal_price=signal_price,
            signal_date=self._get_prev_time(fill_time),
            fill_price=fill_price,
            fill_date=fill_time,
            quantity=quantity,
            commission=commission,
        )
        self.trades.append(filled)
        logger.info(
            f"매도 체결: {order.symbol} {quantity}주 @ {fill_price:.2f} "
            f"(수수료: {commission:.2f})"
        )

    def _get_prev_close(self, symbol: str, current_time) -> float:
        """현재 봉 기준 이전 봉의 종가 반환"""
        df = self.data[symbol]
        idx = df.index.get_loc(current_time)
        if idx > 0:
            return df.iloc[idx - 1]["close"]
        return df.iloc[0]["close"]

    def _get_prev_time(self, current_time):
        """현재 봉 기준 이전 봉의 시간 반환"""
        # 첫 번째 데이터의 인덱스를 기준으로
        first_df = next(iter(self.data.values()))
        idx = first_df.index.get_loc(current_time)
        if idx > 0:
            return first_df.index[idx - 1]
        return first_df.index[0]
