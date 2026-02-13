from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.engine.order import OrderSide, PendingOrder

from .base import Strategy


class MeanReversionStrategy(Strategy):
    """
    평균회귀 전략.
    가격이 이동평균에서 일정 Z-Score 이상 벗어나면 평균 회귀를 기대하고 진입.
    종목별로 독립적인 상태를 유지한다.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 0.5,
            "position_weight": 0.3,
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: "Portfolio"
    ) -> List[PendingOrder]:
        orders = []
        lookback = self.parameters["lookback_period"]

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            state["price_history"].append(close)

            if len(state["price_history"]) < lookback:
                continue

            prices = np.array(state["price_history"][-lookback:])
            mean = np.mean(prices)
            std = np.std(prices)

            if std == 0:
                continue

            z_score = (close - mean) / std
            position = portfolio.get_position(symbol)

            # 과매도 → 매수
            if z_score < -self.parameters["entry_threshold"] and position is None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=self.parameters["position_weight"],
                        reason=f"Z-Score={z_score:.2f} < -{self.parameters['entry_threshold']}",
                    )
                )

            # 평균 회귀 → 매도
            elif position and z_score > -self.parameters["exit_threshold"]:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        weight=1.0,
                        reason=f"Z-Score={z_score:.2f} > -{self.parameters['exit_threshold']}",
                    )
                )

        return orders
