"""CLI 통합 테스트"""

from unittest.mock import patch, MagicMock, AsyncMock

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def _make_sample_df(n=100):
    """테스트용 OHLCV DataFrame 생성"""
    dates = pd.bdate_range("2023-01-01", periods=n)
    np.random.seed(42)
    base = 70000.0
    prices = base * np.cumprod(1 + np.random.normal(0, 0.02, n))
    return pd.DataFrame(
        {
            "open": prices * (1 + np.random.uniform(-0.01, 0.01, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.015, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.015, n))),
            "close": prices,
            "volume": np.random.randint(500000, 2000000, n),
        },
        index=dates,
    )


class TestCLIHelp:
    def test_main_help(self):
        """메인 --help 출력"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "백테스팅" in result.output or "qbt" in result.output

    def test_backtest_help(self):
        """backtest --help"""
        result = runner.invoke(app, ["backtest", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "list" in result.output
        assert "show" in result.output

    def test_data_help(self):
        """data --help"""
        result = runner.invoke(app, ["data", "--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "batch-download" in result.output
        assert "presets" in result.output

    def test_batch_download_help(self):
        """batch-download --help"""
        result = runner.invoke(app, ["data", "batch-download", "--help"])
        assert result.exit_code == 0
        assert "--preset" in result.output
        assert "--symbols" in result.output
        assert "--start" in result.output
        assert "--end" in result.output

    def test_optimize_help(self):
        """optimize --help"""
        result = runner.invoke(app, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output


def _patch_data_provider():
    """KIS API 대신 샘플 데이터를 반환하도록 mock"""
    sample_df = _make_sample_df()

    async def _fake_fetch(*args, **kwargs):
        return sample_df

    async def _fake_close():
        pass

    mock_cached = MagicMock()
    mock_cached.fetch_ohlcv = _fake_fetch

    mock_provider = MagicMock()
    mock_provider.close = _fake_close

    return patch.multiple(
        "cli.commands.backtest",
        **{},  # placeholder
    ), mock_cached, mock_provider


class TestBacktestRun:
    def _run_with_mock(self, args):
        """KIS API를 mock하고 CLI 명령 실행"""
        sample_df = _make_sample_df()

        async def _fake_fetch(*a, **kw):
            return sample_df

        async def _fake_close():
            pass

        mock_cached = MagicMock()
        mock_cached.fetch_ohlcv = _fake_fetch

        mock_provider = MagicMock()
        mock_provider.close = _fake_close

        with patch("cli.commands.backtest.CachedDataProvider", return_value=mock_cached), \
             patch("cli.commands.backtest.KISDataProvider", return_value=mock_provider), \
             patch("cli.commands.backtest.SessionLocal", return_value=MagicMock()):
            return runner.invoke(app, args)

    def test_run_with_sample_data(self):
        """샘플 데이터로 backtest run 실행"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--symbol", "005930",
            "--market", "KR",
            "--start", "2023-01-01",
            "--end", "2023-06-30",
            "--capital", "10000000",
        ])
        assert result.exit_code == 0
        assert "백테스팅 결과" in result.output
        assert "총 수익률" in result.output
        assert "초기 자본금" in result.output

    def test_run_us_market(self):
        """미국 시장으로 실행"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--symbol", "AAPL",
            "--market", "US",
            "--start", "2023-01-01",
            "--end", "2023-06-30",
            "--capital", "100000",
        ])
        assert result.exit_code == 0
        assert "백테스팅 결과" in result.output

    def test_run_invalid_strategy(self):
        """없는 전략명"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "NonExistent",
                "--symbol", "005930",
                "--start", "2023-01-01",
                "--end", "2023-06-30",
            ],
        )
        assert result.exit_code == 1

    def test_run_invalid_date_range(self):
        """시작일 > 종료일"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "mean_reversion",
                "--symbol", "005930",
                "--start", "2023-06-30",
                "--end", "2023-01-01",
            ],
        )
        assert result.exit_code == 1

    def test_run_invalid_date_format(self):
        """잘못된 날짜 형식"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "mean_reversion",
                "--symbol", "005930",
                "--start", "2023/01/01",
                "--end", "2023-06-30",
            ],
        )
        assert result.exit_code != 0

    def test_run_hourly_timeframe(self):
        """시간봉 백테스트"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--symbol", "005930",
            "--market", "KR",
            "--start", "2023-01-01",
            "--end", "2023-03-31",
            "--timeframe", "1h",
        ])
        assert result.exit_code == 0

    def test_run_with_trades(self):
        """거래가 발생하는 기간"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--symbol", "005930",
            "--start", "2023-01-01",
            "--end", "2023-12-31",
            "--capital", "10000000",
        ])
        assert result.exit_code == 0
        assert "총 거래 수" in result.output

    def test_run_with_symbols(self):
        """--symbols로 여러 종목 백테스트"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--symbols", "005930,000660",
            "--market", "KR",
            "--start", "2023-01-01",
            "--end", "2023-06-30",
        ])
        assert result.exit_code == 0
        assert "2개" in result.output

    def test_run_with_preset(self):
        """--preset으로 프리셋 백테스트"""
        result = self._run_with_mock([
            "backtest", "run",
            "--strategy", "mean_reversion",
            "--preset", "kospi10",
            "--start", "2023-01-01",
            "--end", "2023-06-30",
        ])
        assert result.exit_code == 0
        assert "10개" in result.output
        assert "프리셋: kospi10" in result.output

    def test_run_mutual_exclusive_options(self):
        """--symbol과 --symbols 동시 사용 불가"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "mean_reversion",
                "--symbol", "005930",
                "--symbols", "005930,000660",
                "--start", "2023-01-01",
                "--end", "2023-06-30",
            ],
        )
        assert result.exit_code == 1
        assert "동시에 사용할 수 없습니다" in result.output

    def test_run_no_symbol_option(self):
        """종목 옵션 미지정 시 에러"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "mean_reversion",
                "--start", "2023-01-01",
                "--end", "2023-06-30",
            ],
        )
        assert result.exit_code == 1
        assert "하나를 지정해야 합니다" in result.output

    def test_run_invalid_preset(self):
        """존재하지 않는 프리셋"""
        result = runner.invoke(
            app,
            [
                "backtest", "run",
                "--strategy", "mean_reversion",
                "--preset", "nonexistent",
                "--start", "2023-01-01",
                "--end", "2023-06-30",
            ],
        )
        assert result.exit_code == 1
        assert "찾을 수 없습니다" in result.output


class TestBatchDownloadValidation:
    def test_mutual_exclusive_preset_and_symbols(self):
        """--preset과 --symbols 동시 사용 불가"""
        result = runner.invoke(
            app,
            [
                "data", "batch-download",
                "--preset", "kospi10",
                "--symbols", "005930",
                "--start", "2024-01-01",
                "--end", "2024-12-31",
            ],
        )
        assert result.exit_code == 1
        assert "동시에 사용할 수 없습니다" in result.output

    def test_neither_preset_nor_symbols(self):
        """--preset도 --symbols도 없으면 에러"""
        result = runner.invoke(
            app,
            [
                "data", "batch-download",
                "--start", "2024-01-01",
                "--end", "2024-12-31",
            ],
        )
        assert result.exit_code == 1
        assert "하나를 지정하세요" in result.output

    def test_invalid_preset(self):
        """존재하지 않는 프리셋"""
        result = runner.invoke(
            app,
            [
                "data", "batch-download",
                "--preset", "nonexistent",
                "--start", "2024-01-01",
                "--end", "2024-12-31",
            ],
        )
        assert result.exit_code == 1
        assert "Unknown preset" in result.output


class TestPresetsCommand:
    def test_presets_list(self):
        """presets 명령이 프리셋 목록을 출력"""
        result = runner.invoke(app, ["data", "presets"])
        assert result.exit_code == 0
        assert "kospi10" in result.output
        assert "mag7" in result.output


class TestOptimizePlaceholder:
    def test_optimize_not_implemented(self):
        """optimize 미구현 메시지"""
        result = runner.invoke(
            app,
            [
                "optimize", "run",
                "--strategy", "MeanReversion",
                "--symbol", "005930",
            ],
        )
        assert result.exit_code == 0
        assert "Phase 5" in result.output
