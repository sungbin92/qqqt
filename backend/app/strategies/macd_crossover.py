from typing import Any, Dict, List

import pandas as pd
import pandas_ta as ta

from app.engine.order import OrderSide, PendingOrder

from .base import Strategy


class MACDCrossoverStrategy(Strategy):
    """
    MACD 크로스오버 전략.
    MACD선이 시그널선을 상향 돌파(골든크로스)하면 매수,
    MACD선이 시그널선을 하향 돌파(데드크로스)하면 매도.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        defaults = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "position_weight": 0.3,
        }
        if parameters:
            defaults.update(parameters)
        super().__init__(defaults)

    def _init_state(self) -> Dict[str, Any]:
        return {
            "price_history": [],
            "volume_history": [],
            "prev_macd": None,
            "prev_signal": None,
        }

    def on_bar(
        self, bars: Dict[str, pd.Series], portfolio: "Portfolio"
    ) -> List[PendingOrder]:
        orders = []
        fast = self.parameters["fast_period"]
        slow = self.parameters["slow_period"]
        signal_period = self.parameters["signal_period"]
        min_bars = slow + signal_period

        for symbol, bar in bars.items():
            state = self._get_state(symbol)
            close = float(bar["close"])
            state["price_history"].append(close)

            if len(state["price_history"]) < min_bars:
                continue

            series = pd.Series(state["price_history"])
            macd_df = ta.macd(series, fast=fast, slow=slow, signal=signal_period)
            if macd_df is None or macd_df.empty:
                continue

            macd_val = macd_df.iloc[-1, 0]  # MACD line
            signal_val = macd_df.iloc[-1, 2]  # Signal line

            if pd.isna(macd_val) or pd.isna(signal_val):
                state["prev_macd"] = None
                state["prev_signal"] = None
                continue

            prev_macd = state["prev_macd"]
            prev_signal = state["prev_signal"]

            state["prev_macd"] = macd_val
            state["prev_signal"] = signal_val

            if prev_macd is None or prev_signal is None:
                continue

            position = portfolio.get_position(symbol)

            # 골든크로스: MACD가 시그널선을 상향 돌파
            if prev_macd <= prev_signal and macd_val > signal_val and position is None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        weight=self.parameters["position_weight"],
                        reason=f"MACD골든크로스: {macd_val:.2f} > {signal_val:.2f}",
                    )
                )

            # 데드크로스: MACD가 시그널선을 하향 돌파
            elif prev_macd >= prev_signal and macd_val < signal_val and position is not None:
                orders.append(
                    PendingOrder(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        weight=1.0,
                        reason=f"MACD데드크로스: {macd_val:.2f} < {signal_val:.2f}",
                    )
                )

        return orders
