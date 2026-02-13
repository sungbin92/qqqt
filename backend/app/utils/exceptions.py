from typing import Optional


class BacktestError(Exception):
    """백테스팅 시스템 기본 예외"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


# ── 400 Bad Request ──


class InvalidDateRangeError(BacktestError):
    def __init__(self, message: str = "시작일이 종료일보다 미래입니다"):
        super().__init__(message, "INVALID_DATE_RANGE", 400)


class PeriodTooShortError(BacktestError):
    def __init__(self, message: str = "최소 백테스팅 기간 미달"):
        super().__init__(message, "PERIOD_TOO_SHORT", 400)


class InsufficientCapitalError(BacktestError):
    def __init__(self, message: str = "최소 자본금 미달"):
        super().__init__(message, "INSUFFICIENT_CAPITAL", 400)


class TooManyCombinationsError(BacktestError):
    def __init__(self, message: str = "최적화 조합 수 초과 (최대 10,000)"):
        super().__init__(message, "TOO_MANY_COMBINATIONS", 400)


class InsufficientDataError(BacktestError):
    def __init__(self, message: str = "해당 기간 데이터 부족"):
        super().__init__(message, "INSUFFICIENT_DATA", 400)


# ── 404 Not Found ──


class BacktestNotFoundError(BacktestError):
    def __init__(self, backtest_id: Optional[str] = None):
        msg = f"백테스팅을 찾을 수 없습니다: {backtest_id}" if backtest_id else "백테스팅 ID 없음"
        super().__init__(msg, "BACKTEST_NOT_FOUND", 404)


class StrategyNotFoundError(BacktestError):
    def __init__(self, strategy_name: Optional[str] = None):
        msg = f"전략을 찾을 수 없습니다: {strategy_name}" if strategy_name else "전략 이름 없음"
        super().__init__(msg, "STRATEGY_NOT_FOUND", 404)


# ── 429 Rate Limit ──


class KISRateLimitError(BacktestError):
    def __init__(self, message: str = "한국투자증권 API 호출 제한"):
        super().__init__(message, "KIS_RATE_LIMIT", 429)


# ── 500 Internal Server Error ──


class EngineError(BacktestError):
    def __init__(self, message: str = "백테스팅 엔진 내부 오류"):
        super().__init__(message, "ENGINE_ERROR", 500)


# ── 503 Service Unavailable ──


class KISAPIUnavailableError(BacktestError):
    def __init__(self, message: str = "한국투자증권 API 응답 없음"):
        super().__init__(message, "KIS_API_UNAVAILABLE", 503)
