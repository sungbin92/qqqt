import numpy as np
import pandas as pd


class PerformanceMetrics:
    """성과 지표 계산 (벡터화 연산)"""

    @staticmethod
    def calculate_returns(equity_curve: pd.Series) -> pd.Series:
        return equity_curve.pct_change().fillna(0)

    @staticmethod
    def total_return(equity_curve: pd.Series) -> float:
        return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    @staticmethod
    def annual_return(equity_curve: pd.Series, trading_days: int = 252) -> float:
        total_days = len(equity_curve)
        years = total_days / trading_days
        total_ret = PerformanceMetrics.total_return(equity_curve)
        if years <= 0:
            return 0
        return (1 + total_ret) ** (1 / years) - 1

    @staticmethod
    def sharpe_ratio(
        equity_curve: pd.Series,
        risk_free_rate: float = 0.02,
        trading_days: int = 252,
    ) -> float:
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        excess = returns - risk_free_rate / trading_days
        if returns.std() == 0:
            return 0
        return np.sqrt(trading_days) * excess.mean() / returns.std()

    @staticmethod
    def sortino_ratio(
        equity_curve: pd.Series,
        risk_free_rate: float = 0.02,
        trading_days: int = 252,
    ) -> float:
        returns = PerformanceMetrics.calculate_returns(equity_curve)
        excess = returns - risk_free_rate / trading_days
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 0
        return np.sqrt(trading_days) * excess.mean() / downside.std()

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> float:
        cummax = equity_curve.expanding().max()
        dd = (equity_curve - cummax) / cummax
        return abs(dd.min())

    @staticmethod
    def win_rate(trades: pd.DataFrame) -> float:
        if len(trades) == 0:
            return 0
        return (trades["pnl"] > 0).sum() / len(trades)

    @staticmethod
    def profit_factor(trades: pd.DataFrame) -> float:
        if len(trades) == 0:
            return 0
        gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(trades[trades["pnl"] < 0]["pnl"].sum())
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0
        return gross_profit / gross_loss

    @staticmethod
    def max_consecutive(trades: pd.DataFrame, win: bool = True) -> int:
        """최대 연속 승/패"""
        if len(trades) == 0:
            return 0
        results = (trades["pnl"] > 0) if win else (trades["pnl"] <= 0)
        max_streak = current = 0
        for r in results:
            if r:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak
