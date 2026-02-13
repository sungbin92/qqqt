from typing import Any, Dict, List

import pandas as pd
import pandas_ta as ta

from app.engine.order import OrderSide, PendingOrder

from .base import Strategy


class RSIStrategy(Strategy):
    """
    RSI 전략.
    RSI가 과매도 기준 이하이면 매수,
    RSI가 과매수 기준 이상이면 매도.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "position_weight": 0.3,
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: "Portfolio"
    ) -> List[PendingOrder]:
        orders = []
        rsi_period = self.parameters["rsi_period"]

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            state["price_history"].append(close)

            # RSI 계산에 최소 rsi_period + 1개 데이터 필요
            if len(state["price_history"]) < rsi_period + 1:
                continue

            series = pd.Series(state["price_history"])
            rsi_series = ta.rsi(series, length=rsi_period)
            if rsi_series is None or rsi_series.empty:
                continue

            rsi_value = rsi_series.iloc[-1]
            if pd.isna(rsi_value):
                continue

            position = portfolio.get_position(symbol)

            # 과매도 → 매수
            if rsi_value < self.parameters["oversold_threshold"] and position is None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=self.parameters["position_weight"],
                        reason=f"RSI과매도: {rsi_value:.1f} < {self.parameters['oversold_threshold']}",
                    )
                )

            # 과매수 → 매도
            elif rsi_value > self.parameters["overbought_threshold"] and position is not None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        weight=1.0,
                        reason=f"RSI과매수: {rsi_value:.1f} > {self.parameters['overbought_threshold']}",
                    )
                )

        return orders
