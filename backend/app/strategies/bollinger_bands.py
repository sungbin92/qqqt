from typing import Any, Dict, List

import pandas as pd
import pandas_ta as ta

from app.engine.order import OrderSide, PendingOrder

from .base import Strategy


class BollingerBandsStrategy(Strategy):
    """
    볼린저 밴드 전략.
    가격이 하단 밴드 이하이면 과매도로 매수,
    가격이 상단 밴드 이상이면 과매수로 매도.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "bb_period": 20,
            "bb_std": 2.0,
            "position_weight": 0.3,
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: "Portfolio"
    ) -> List[PendingOrder]:
        orders = []
        bb_period = self.parameters["bb_period"]
        bb_std = self.parameters["bb_std"]

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            state["price_history"].append(close)

            if len(state["price_history"]) < bb_period:
                continue

            series = pd.Series(state["price_history"][-bb_period:])
            bb = ta.bbands(series, length=bb_period, std=bb_std)
            if bb is None or bb.empty:
                continue

            lower = bb.iloc[-1, 0]  # BBL
            upper = bb.iloc[-1, 2]  # BBU

            position = portfolio.get_position(symbol)

            # 과매도 → 매수
            if close <= lower and position is None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=self.parameters["position_weight"],
                        reason=f"BB하단돌파: {close:.0f} <= {lower:.0f}",
                    )
                )

            # 과매수 → 매도
            elif close >= upper and position is not None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        weight=1.0,
                        reason=f"BB상단돌파: {close:.0f} >= {upper:.0f}",
                    )
                )

        return orders
