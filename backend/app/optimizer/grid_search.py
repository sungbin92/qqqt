"""Grid Search 기반 파라미터 최적화"""

import itertools
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from app.analytics.performance import PerformanceMetrics
from app.config import MARKET_CONFIGS
from app.engine.backtest import BacktestEngine
from app.engine.broker import Broker
from app.strategies import get_strategy
from app.utils.exceptions import TooManyCombinationsError
from app.utils.logger import logger

MAX_COMBINATIONS = 10_000


def generate_combinations(parameter_ranges: Dict[str, Dict[str, float]]) -> List[Dict[str, float]]:
    """
    파라미터 범위에서 모든 조합을 생성.

    Args:
        parameter_ranges: {param_name: {"min": float, "max": float, "step": float}}

    Returns:
        List of parameter dicts
    """
    if not parameter_ranges:
        return [{}]

    param_names = sorted(parameter_ranges.keys())
    param_values = []

    for name in param_names:
        r = parameter_ranges[name]
        values = np.arange(r["min"], r["max"] + r["step"] * 0.5, r["step"]).tolist()
        # 부동소수점 정리
        values = [round(v, 10) for v in values]
        param_values.append(values)

    combinations = []
    for combo in itertools.product(*param_values):
        combinations.append(dict(zip(param_names, combo)))

    return combinations


def count_combinations(parameter_ranges: Dict[str, Dict[str, float]]) -> int:
    """조합 수 사전 계산 (실제 생성 없이)."""
    if not parameter_ranges:
        return 1

    count = 1
    for r in parameter_ranges.values():
        n = len(np.arange(r["min"], r["max"] + r["step"] * 0.5, r["step"]))
        count *= n
    return count


def run_grid_search(
    strategy_name: str,
    combinations: List[Dict[str, float]],
    data: Dict,
    market: str,
    timeframe: str,
    initial_capital: float,
    optimization_metric: str = "sharpe_ratio",
    on_progress: Optional[Callable[[int], None]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Grid Search 실행.

    각 파라미터 조합으로 백테스트를 돌리고, optimization_metric 기준 상위 top_n개 반환.
    """
    results = []
    total = len(combinations)
    market_config = MARKET_CONFIGS[market]
    trading_days = market_config.trading_days_per_year

    for i, params in enumerate(combinations):
        try:
            strategy = get_strategy(strategy_name, params)
            broker = Broker(market, timeframe)
            engine = BacktestEngine(
                strategy=strategy,
                data=data,
                broker=broker,
                initial_capital=initial_capital,
            )
            result = engine.run()

            equity_curve_df = result["equity_curve"]
            metrics: Dict[str, Any] = {"parameters": params}

            if not equity_curve_df.empty:
                equity_series = equity_curve_df["equity"]
                metrics["total_return"] = PerformanceMetrics.total_return(equity_series)
                metrics["annual_return"] = PerformanceMetrics.annual_return(
                    equity_series, trading_days
                )
                metrics["sharpe_ratio"] = PerformanceMetrics.sharpe_ratio(
                    equity_series, trading_days=trading_days
                )
                metrics["sortino_ratio"] = PerformanceMetrics.sortino_ratio(
                    equity_series, trading_days=trading_days
                )
                metrics["max_drawdown"] = PerformanceMetrics.max_drawdown(equity_series)
                metrics["total_trades"] = len(result["trades"])
                metrics["final_equity"] = result["final_equity"]
            else:
                metrics["total_return"] = 0
                metrics["annual_return"] = 0
                metrics["sharpe_ratio"] = 0
                metrics["sortino_ratio"] = 0
                metrics["max_drawdown"] = 0
                metrics["total_trades"] = 0
                metrics["final_equity"] = initial_capital

            results.append(metrics)

        except Exception as e:
            logger.warning("조합 %d/%d 실패 (params=%s): %s", i + 1, total, params, e)
            continue

        if on_progress:
            pct = int((i + 1) / total * 100)
            on_progress(pct)

    # optimization_metric 기준 내림차순 정렬 (max_drawdown은 절대값이 작을수록 좋으므로 오름차순)
    reverse = optimization_metric != "max_drawdown"
    results.sort(key=lambda r: r.get(optimization_metric, 0) or 0, reverse=reverse)

    return results[:top_n]
