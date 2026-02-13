import math

import numpy as np
import pandas as pd
import pytest

from app.analytics.performance import PerformanceMetrics
from app.analytics.risk import RiskMetrics


# ── Fixtures ──


@pytest.fixture
def simple_equity():
    """100 → 110 선형 상승 (10일)"""
    return pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110], dtype=float)


@pytest.fixture
def trades_mixed():
    """승 3, 패 2, 승 1 → max_consecutive_wins=3"""
    return pd.DataFrame({"pnl": [100, 200, 50, -30, -10, 80]})


@pytest.fixture
def trades_all_win():
    return pd.DataFrame({"pnl": [100, 200, 50, 30]})


@pytest.fixture
def trades_all_loss():
    return pd.DataFrame({"pnl": [-100, -200, -50, -30]})


@pytest.fixture
def trades_empty():
    return pd.DataFrame({"pnl": []})


# ── calculate_returns ──


class TestCalculateReturns:
    def test_first_return_is_zero(self, simple_equity):
        returns = PerformanceMetrics.calculate_returns(simple_equity)
        assert returns.iloc[0] == 0

    def test_returns_length(self, simple_equity):
        returns = PerformanceMetrics.calculate_returns(simple_equity)
        assert len(returns) == len(simple_equity)

    def test_known_return(self):
        eq = pd.Series([100.0, 110.0])
        returns = PerformanceMetrics.calculate_returns(eq)
        assert pytest.approx(returns.iloc[1], rel=1e-6) == 0.1


# ── total_return ──


class TestTotalReturn:
    def test_known_total_return(self, simple_equity):
        # 100 → 110 = 10%
        assert pytest.approx(PerformanceMetrics.total_return(simple_equity), rel=1e-6) == 0.1

    def test_negative_return(self):
        eq = pd.Series([100.0, 90.0])
        assert pytest.approx(PerformanceMetrics.total_return(eq), rel=1e-6) == -0.1


# ── annual_return ──


class TestAnnualReturn:
    def test_annual_return_one_year(self):
        # 252개 데이터포인트, total_return=10% → years=1 → annual=10%
        eq = pd.Series(np.linspace(100, 110, 252))
        result = PerformanceMetrics.annual_return(eq, trading_days=252)
        assert pytest.approx(result, rel=1e-4) == 0.1

    def test_annual_return_half_year(self):
        # 126일(반년) 동안 10% → 연환산 ≈ 21%
        eq = pd.Series(np.linspace(100, 110, 126))
        result = PerformanceMetrics.annual_return(eq, trading_days=252)
        expected = (1.1) ** 2 - 1  # ≈ 0.21
        assert pytest.approx(result, rel=1e-2) == expected


# ── sharpe_ratio ──


class TestSharpeRatio:
    def test_positive_sharpe(self):
        # 꾸준히 상승하는 equity → 양의 Sharpe
        eq = pd.Series(np.linspace(100, 120, 252))
        sharpe = PerformanceMetrics.sharpe_ratio(eq)
        assert sharpe > 0

    def test_zero_std_returns_zero(self):
        eq = pd.Series([100.0] * 10)
        assert PerformanceMetrics.sharpe_ratio(eq) == 0

    def test_known_sharpe(self):
        # 수동 계산과 비교
        eq = pd.Series([100.0, 101.0, 102.0, 101.5, 103.0])
        returns = eq.pct_change().fillna(0)
        excess = returns - 0.02 / 252
        expected = np.sqrt(252) * excess.mean() / returns.std()
        result = PerformanceMetrics.sharpe_ratio(eq)
        assert pytest.approx(result, rel=1e-6) == expected


# ── sortino_ratio ──


class TestSortinoRatio:
    def test_positive_sortino(self):
        eq = pd.Series(np.linspace(100, 120, 252))
        sortino = PerformanceMetrics.sortino_ratio(eq)
        # 선형 상승 → 하방 변동성 없음 → sortino = 0
        assert sortino == 0

    def test_sortino_with_downside(self):
        # 상승/하락 혼합
        eq = pd.Series([100, 105, 102, 108, 103, 110], dtype=float)
        sortino = PerformanceMetrics.sortino_ratio(eq)
        # 하방 변동성 존재하고 전체적으로 상승 → 양수
        assert sortino > 0

    def test_no_downside_returns_zero(self):
        # 모든 수익률이 양수 또는 0
        eq = pd.Series([100.0, 100.0, 101.0, 102.0])
        assert PerformanceMetrics.sortino_ratio(eq) == 0


# ── max_drawdown ──


class TestMaxDrawdown:
    def test_no_drawdown(self):
        eq = pd.Series([100.0, 101.0, 102.0, 103.0])
        assert PerformanceMetrics.max_drawdown(eq) == 0

    def test_known_drawdown(self):
        # 100 → 120 → 96 → 110
        # 최대 낙폭: (120-96)/120 = 20%
        eq = pd.Series([100.0, 120.0, 96.0, 110.0])
        assert pytest.approx(PerformanceMetrics.max_drawdown(eq), rel=1e-6) == 0.2

    def test_drawdown_at_end(self):
        # 100 → 200 → 150
        # 최대 낙폭: (200-150)/200 = 25%
        eq = pd.Series([100.0, 200.0, 150.0])
        assert pytest.approx(PerformanceMetrics.max_drawdown(eq), rel=1e-6) == 0.25


# ── win_rate ──


class TestWinRate:
    def test_mixed_trades(self, trades_mixed):
        # 4 wins out of 6
        assert pytest.approx(PerformanceMetrics.win_rate(trades_mixed), rel=1e-6) == 4 / 6

    def test_all_wins(self, trades_all_win):
        assert PerformanceMetrics.win_rate(trades_all_win) == 1.0

    def test_all_losses(self, trades_all_loss):
        assert PerformanceMetrics.win_rate(trades_all_loss) == 0.0

    def test_empty_trades(self, trades_empty):
        assert PerformanceMetrics.win_rate(trades_empty) == 0


# ── profit_factor ──


class TestProfitFactor:
    def test_known_profit_factor(self, trades_mixed):
        # gross_profit = 100+200+50+80 = 430
        # gross_loss = 30+10 = 40
        expected = 430 / 40
        assert pytest.approx(PerformanceMetrics.profit_factor(trades_mixed), rel=1e-6) == expected

    def test_all_wins_returns_inf(self, trades_all_win):
        assert PerformanceMetrics.profit_factor(trades_all_win) == float("inf")

    def test_all_losses_returns_zero(self, trades_all_loss):
        # gross_profit = 0, gross_loss > 0 → 0/loss = 0... but spec says inf if profit>0 else 0
        # all losses: gross_profit = 0, gross_loss > 0 → loss == 0? No, loss > 0
        # gross_profit = 0, gross_loss > 0 → 0 / gross_loss = 0
        assert PerformanceMetrics.profit_factor(trades_all_loss) == 0

    def test_empty_trades(self, trades_empty):
        assert PerformanceMetrics.profit_factor(trades_empty) == 0

    def test_no_loss_no_profit(self):
        # pnl = 0인 거래만
        trades = pd.DataFrame({"pnl": [0, 0, 0]})
        assert PerformanceMetrics.profit_factor(trades) == 0


# ── max_consecutive ──


class TestMaxConsecutive:
    def test_consecutive_wins(self, trades_mixed):
        # pnl: [100, 200, 50, -30, -10, 80] → 승승승 패패 승 → max_consecutive_wins = 3
        assert PerformanceMetrics.max_consecutive(trades_mixed, win=True) == 3

    def test_consecutive_losses(self, trades_mixed):
        # pnl: [100, 200, 50, -30, -10, 80] → max_consecutive_losses = 2
        assert PerformanceMetrics.max_consecutive(trades_mixed, win=False) == 2

    def test_all_wins(self, trades_all_win):
        assert PerformanceMetrics.max_consecutive(trades_all_win, win=True) == 4
        assert PerformanceMetrics.max_consecutive(trades_all_win, win=False) == 0

    def test_all_losses(self, trades_all_loss):
        assert PerformanceMetrics.max_consecutive(trades_all_loss, win=True) == 0
        assert PerformanceMetrics.max_consecutive(trades_all_loss, win=False) == 4

    def test_empty_trades(self, trades_empty):
        assert PerformanceMetrics.max_consecutive(trades_empty, win=True) == 0
        assert PerformanceMetrics.max_consecutive(trades_empty, win=False) == 0


# ── RiskMetrics: calmar_ratio ──


class TestCalmarRatio:
    def test_positive_calmar(self):
        # 100 → 120 → 108 → 130 (MDD = 12/120 = 10%, annual_return > 0)
        eq = pd.Series([100.0, 120.0, 108.0, 130.0])
        calmar = RiskMetrics.calmar_ratio(eq)
        expected = PerformanceMetrics.annual_return(eq) / PerformanceMetrics.max_drawdown(eq)
        assert pytest.approx(calmar, rel=1e-6) == expected

    def test_no_drawdown_returns_zero(self):
        eq = pd.Series([100.0, 101.0, 102.0, 103.0])
        assert RiskMetrics.calmar_ratio(eq) == 0


# ── RiskMetrics: value_at_risk ──


class TestValueAtRisk:
    def test_var_positive(self):
        # 변동성이 있는 equity → VaR > 0
        eq = pd.Series([100, 102, 98, 105, 97, 103, 99, 106, 95, 108], dtype=float)
        var = RiskMetrics.value_at_risk(eq)
        assert var > 0

    def test_var_known_value(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 1000)
        equity = pd.Series(100 * np.cumprod(1 + returns))
        var = RiskMetrics.value_at_risk(equity, confidence=0.95)

        # 수동 계산
        calc_returns = equity.pct_change().fillna(0)
        expected = abs(np.percentile(calc_returns, 5))
        assert pytest.approx(var, rel=1e-6) == expected

    def test_var_no_volatility(self):
        eq = pd.Series([100.0] * 10)
        assert RiskMetrics.value_at_risk(eq) == 0

    def test_var_empty_returns_zero(self):
        eq = pd.Series([100.0])
        # 1개 데이터 → returns는 [0] → std=0
        assert RiskMetrics.value_at_risk(eq) == 0
