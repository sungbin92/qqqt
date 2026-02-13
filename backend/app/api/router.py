"""API 라우터 통합"""

from fastapi import APIRouter

from app.api.backtest import router as backtest_router
from app.api.compare import router as compare_router
from app.api.data import router as data_router
from app.api.optimize import router as optimize_router
from app.api.strategies import router as strategies_router

api_router = APIRouter()
# compare 라우터를 backtest보다 먼저 등록 (/api/backtest/compare vs /api/backtest/{id})
api_router.include_router(compare_router)
api_router.include_router(backtest_router)
api_router.include_router(strategies_router)
api_router.include_router(data_router)
api_router.include_router(optimize_router)
