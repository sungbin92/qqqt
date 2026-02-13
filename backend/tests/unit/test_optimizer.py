"""파라미터 최적화 (Grid Search) 단위 테스트"""

import pytest

from app.optimizer.grid_search import (
    count_combinations,
    generate_combinations,
    run_grid_search,
)
from app.utils.exceptions import TooManyCombinationsError


class TestGenerateCombinations:
    def test_single_param(self):
        ranges = {"lookback": {"min": 10, "max": 30, "step": 10}}
        combos = generate_combinations(ranges)
        assert len(combos) == 3
        values = [c["lookback"] for c in combos]
        assert 10 in values
        assert 20 in values
        assert 30 in values

    def test_two_params(self):
        ranges = {
            "a": {"min": 1, "max": 2, "step": 1},
            "b": {"min": 0.1, "max": 0.3, "step": 0.1},
        }
        combos = generate_combinations(ranges)
        assert len(combos) == 2 * 3  # a: [1,2], b: [0.1, 0.2, 0.3]

    def test_empty_ranges(self):
        combos = generate_combinations({})
        assert combos == [{}]

    def test_single_value_range(self):
        ranges = {"x": {"min": 5, "max": 5, "step": 1}}
        combos = generate_combinations(ranges)
        assert len(combos) == 1
        assert combos[0]["x"] == 5


class TestCountCombinations:
    def test_count_matches_generate(self):
        ranges = {
            "a": {"min": 1, "max": 5, "step": 1},
            "b": {"min": 0.1, "max": 0.5, "step": 0.1},
        }
        count = count_combinations(ranges)
        combos = generate_combinations(ranges)
        assert count == len(combos)

    def test_empty(self):
        assert count_combinations({}) == 1

    def test_large_count(self):
        """10,000개 초과 시나리오 검증"""
        ranges = {
            "a": {"min": 1, "max": 100, "step": 1},    # 100
            "b": {"min": 1, "max": 101, "step": 1},     # 101
        }
        count = count_combinations(ranges)
        assert count > 10_000


class TestTooManyCombinations:
    def test_error_raised(self):
        err = TooManyCombinationsError()
        assert err.status_code == 400
        assert err.error_code == "TOO_MANY_COMBINATIONS"


class TestTopNSelection:
    """run_grid_search의 상위 N개 선택 검증 (mock 데이터 사용)"""

    def test_top_n_selection(self):
        """간단한 데이터로 상위 결과 선택 검증"""
        import pandas as pd
        import numpy as np

        # 최소한의 OHLCV 데이터 생성 (100봉)
        dates = pd.date_range("2023-01-01", periods=100, freq="B")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

        df = pd.DataFrame(
            {
                "open": prices,
                "high": prices + 1,
                "low": prices - 1,
                "close": prices,
                "volume": np.random.randint(1000, 10000, 100),
            },
            index=dates,
        )
        data = {"005930": df}

        # 3개 조합 (lookback 10, 20, 30)
        combos = [
            {"lookback_period": 10, "entry_threshold": 2.0, "exit_threshold": 0.5, "position_weight": 0.3},
            {"lookback_period": 20, "entry_threshold": 2.0, "exit_threshold": 0.5, "position_weight": 0.3},
            {"lookback_period": 30, "entry_threshold": 2.0, "exit_threshold": 0.5, "position_weight": 0.3},
        ]

        results = run_grid_search(
            strategy_name="mean_reversion",
            combinations=combos,
            data=data,
            market="KR",
            timeframe="1d",
            initial_capital=10_000_000,
            optimization_metric="sharpe_ratio",
            top_n=2,
        )

        # 최대 top_n개 반환
        assert len(results) <= 2
        # 각 결과에 필수 키 존재
        for r in results:
            assert "parameters" in r
            assert "sharpe_ratio" in r
            assert "total_return" in r

        # sharpe_ratio 기준 내림차순 정렬
        if len(results) == 2:
            assert (results[0].get("sharpe_ratio") or 0) >= (results[1].get("sharpe_ratio") or 0)

    def test_progress_callback(self):
        """진행률 콜백이 호출되는지 검증"""
        import pandas as pd
        import numpy as np

        dates = pd.date_range("2023-01-01", periods=50, freq="B")
        prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
        df = pd.DataFrame(
            {
                "open": prices,
                "high": prices + 1,
                "low": prices - 1,
                "close": prices,
                "volume": np.random.randint(1000, 10000, 50),
            },
            index=dates,
        )

        progress_values = []
        results = run_grid_search(
            strategy_name="mean_reversion",
            combinations=[
                {"lookback_period": 10, "entry_threshold": 2.0, "exit_threshold": 0.5, "position_weight": 0.3},
                {"lookback_period": 20, "entry_threshold": 2.0, "exit_threshold": 0.5, "position_weight": 0.3},
            ],
            data={"TEST": df},
            market="KR",
            timeframe="1d",
            initial_capital=10_000_000,
            on_progress=lambda pct: progress_values.append(pct),
        )

        assert len(progress_values) > 0
        assert progress_values[-1] == 100
