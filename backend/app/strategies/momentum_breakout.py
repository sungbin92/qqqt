from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.engine.order import OrderSide, PendingOrder

from .base import Strategy


class MomentumBreakoutStrategy(Strategy):
    """
    모멘텀 돌파 전략.
    이동평균 돌파 + 거래량 증가 조건으로 매수,
    손절/익절 기반으로 매도.
    종목별 독립 상태를 유지한다.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "ma_period": 20,
            "volume_ma_period": 20,
            "volume_threshold": 2.0,  # 평균 거래량 대비 배수
            "stop_loss_pct": 0.05,  # 5% 손절
            "take_profit_pct": 0.15,  # 15% 익절
            "position_weight": 0.3,
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def _init_state(self) -> Dict[str, Any]:
        return {
            "price_history": [],
            "volume_history": [],
            "entry_price": None,
        }

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: "Portfolio"
    ) -> List[PendingOrder]:
        orders = []
        ma_period = self.parameters["ma_period"]
        vol_ma_period = self.parameters["volume_ma_period"]
        vol_threshold = self.parameters["volume_threshold"]
        stop_loss_pct = self.parameters["stop_loss_pct"]
        take_profit_pct = self.parameters["take_profit_pct"]

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            volume = float(bar["volume"])

            state["price_history"].append(close)
            state["volume_history"].append(volume)

            position = portfolio.get_position(symbol)

            # 보유 중이면 손절/익절 체크
            if position is not None:
                entry_price = state["entry_price"]
                if entry_price is not None and entry_price > 0:
                    pnl_pct = (close - entry_price) / entry_price

                    # 손절
                    if pnl_pct <= -stop_loss_pct:
                        orders.append(
                            PendingOrder(
                                symbol=symbol,
                                side=OrderSide.SELL,
                                weight=1.0,
                                reason=f"손절: {pnl_pct:.2%} <= -{stop_loss_pct:.0%}",
                            )
                        )
                        state["entry_price"] = None
                        continue

                    # 익절
                    if pnl_pct >= take_profit_pct:
                        orders.append(
                            PendingOrder(
                                symbol=symbol,
                                side=OrderSide.SELL,
                                weight=1.0,
                                reason=f"익절: {pnl_pct:.2%} >= +{take_profit_pct:.0%}",
                            )
                        )
                        state["entry_price"] = None
                        continue

                # 포지션 보유 중이면 매수 시그널 무시
                continue

            # 매수 조건 체크: MA 돌파 + 거래량 급증
            if len(state["price_history"]) < ma_period:
                continue
            if len(state["volume_history"]) < vol_ma_period:
                continue

            prices = np.array(state["price_history"][-ma_period:])
            ma = np.mean(prices)

            volumes = np.array(state["volume_history"][-vol_ma_period:])
            vol_ma = np.mean(volumes)

            # 현재가 > 이동평균 (돌파) & 거래량 > 평균 * threshold
            if vol_ma > 0 and close > ma and volume >= vol_ma * vol_threshold:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=self.parameters["position_weight"],
                        reason=f"MA돌파: {close:.0f}>{ma:.0f}, 거래량 {volume/vol_ma:.1f}x",
                    )
                )
                state["entry_price"] = close

        return orders
