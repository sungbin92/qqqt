import numpy as np
import pandas as pd

from app.analytics.performance import PerformanceMetrics


class RiskMetrics:
    """리스크 지표 계산"""

    @staticmethod
    def calmar_ratio(equity_curve: pd.Series, trading_days: int = 252) -> float:
        """Calmar Ratio = 연환산 수익률 / 최대 낙폭"""
        mdd = PerformanceMetrics.max_drawdown(equity_curve)
        if mdd == 0:
            return 0
        ann_ret = PerformanceMetrics.annual_return(equity_curve, trading_days)
        return ann_ret / mdd

    @staticmethod
    def value_at_risk(equity_curve: pd.Series, confidence: float = 0.95) -> float:
        """일별 VaR (Value at Risk). 양수로 반환 (손실 크기)."""
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        if len(returns) == 0 or returns.std() == 0:
            return 0
        var = np.percentile(returns, (1 - confidence) * 100)
        return abs(var)
