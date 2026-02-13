"""FastAPI 앱 엔트리포인트"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.utils.exceptions import BacktestError
from app.utils.response import error_response

app = FastAPI(
    title="Quant Backtest API",
    description="퀀트 기반 주식 투자 전략 백테스팅 시스템",
    version="0.1.0",
)

# CORS (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)


@app.exception_handler(BacktestError)
async def backtest_error_handler(request: Request, exc: BacktestError):
    """BacktestError 계열 예외를 ApiResponse 형식으로 반환"""
    resp = error_response(error=exc.message, error_code=exc.error_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=resp.model_dump(mode="json"),
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
