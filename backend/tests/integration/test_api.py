"""FastAPI API 통합 테스트"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Backtest, JobStatus, MarketType, TimeframeType
from app.db.session import get_db
from app.main import app


# ── 테스트 DB 설정 ──


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_engine):
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(test_engine, test_session):
    """FastAPI TestClient with test DB"""
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── 공통 데이터 ──

VALID_BACKTEST = {
    "name": "테스트 백테스트",
    "description": "테스트용",
    "strategy_name": "mean_reversion",
    "parameters": {"lookback_period": 20, "z_score_entry": 2.0, "z_score_exit": 0.5},
    "market": "KR",
    "symbols": ["005930"],
    "timeframe": "1d",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-06-01T00:00:00",
    "initial_capital": 10000000,
}


# ── POST /api/backtest ──


class TestCreateBacktest:
    @patch("app.api.backtest.run_backtest_task")
    def test_create_success(self, mock_task, client):
        mock_task.delay = MagicMock()

        resp = client.post("/api/backtest", json=VALID_BACKTEST)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "PENDING"
        assert "job_id" in body["data"]
        mock_task.delay.assert_called_once()

    @patch("app.api.backtest.run_backtest_task")
    def test_create_invalid_date_range(self, mock_task, client):
        data = {**VALID_BACKTEST, "start_date": "2024-06-01T00:00:00", "end_date": "2024-01-01T00:00:00"}
        resp = client.post("/api/backtest", json=data)
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "INVALID_DATE_RANGE"

    @patch("app.api.backtest.run_backtest_task")
    def test_create_unknown_strategy(self, mock_task, client):
        data = {**VALID_BACKTEST, "strategy_name": "nonexistent_strategy"}
        resp = client.post("/api/backtest", json=data)
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "STRATEGY_NOT_FOUND"

    @patch("app.api.backtest.run_backtest_task")
    def test_create_insufficient_capital_kr(self, mock_task, client):
        data = {**VALID_BACKTEST, "initial_capital": 1000}  # KR 최소 100,000
        resp = client.post("/api/backtest", json=data)
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "INSUFFICIENT_CAPITAL"

    @patch("app.api.backtest.run_backtest_task")
    def test_create_insufficient_capital_us(self, mock_task, client):
        data = {**VALID_BACKTEST, "market": "US", "symbols": ["AAPL"], "initial_capital": 10}
        resp = client.post("/api/backtest", json=data)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error_code"] == "INSUFFICIENT_CAPITAL"


# ── GET /api/backtest ──


class TestListBacktests:
    @patch("app.api.backtest.run_backtest_task")
    def test_list_empty(self, mock_task, client):
        resp = client.get("/api/backtest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @patch("app.api.backtest.run_backtest_task")
    def test_list_with_items(self, mock_task, client):
        mock_task.delay = MagicMock()

        # 2개 생성
        client.post("/api/backtest", json=VALID_BACKTEST)
        data2 = {**VALID_BACKTEST, "name": "두번째 테스트"}
        client.post("/api/backtest", json=data2)

        resp = client.get("/api/backtest")
        body = resp.json()
        assert body["meta"]["total"] == 2
        assert len(body["data"]) == 2

    @patch("app.api.backtest.run_backtest_task")
    def test_list_pagination(self, mock_task, client):
        mock_task.delay = MagicMock()

        for i in range(5):
            client.post("/api/backtest", json={**VALID_BACKTEST, "name": f"테스트 {i}"})

        resp = client.get("/api/backtest?page=1&limit=2")
        body = resp.json()
        assert body["meta"]["total"] == 5
        assert len(body["data"]) == 2
        assert body["meta"]["page"] == 1


# ── GET /api/backtest/{id} ──


class TestGetBacktest:
    @patch("app.api.backtest.run_backtest_task")
    def test_get_existing(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest", json=VALID_BACKTEST)
        job_id = resp.json()["data"]["job_id"]

        resp = client.get(f"/api/backtest/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["id"] == job_id
        assert body["data"]["strategy_name"] == "mean_reversion"

    def test_get_not_found(self, client):
        resp = client.get("/api/backtest/nonexistent-id")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_code"] == "BACKTEST_NOT_FOUND"


# ── GET /api/backtest/{id}/status ──


class TestGetBacktestStatus:
    @patch("app.api.backtest.run_backtest_task")
    def test_status(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest", json=VALID_BACKTEST)
        job_id = resp.json()["data"]["job_id"]

        resp = client.get(f"/api/backtest/{job_id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "PENDING"
        assert body["data"]["progress"] == 0


# ── DELETE /api/backtest/{id} ──


class TestDeleteBacktest:
    @patch("app.api.backtest.run_backtest_task")
    def test_delete_success(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest", json=VALID_BACKTEST)
        job_id = resp.json()["data"]["job_id"]

        resp = client.delete(f"/api/backtest/{job_id}")
        assert resp.status_code == 200

        # 삭제 확인
        resp = client.get(f"/api/backtest/{job_id}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/backtest/nonexistent-id")
        assert resp.status_code == 404


# ── GET /api/strategies ──


class TestStrategies:
    def test_list_strategies(self, client):
        resp = client.get("/api/strategies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        names = [s["name"] for s in body["data"]]
        assert "mean_reversion" in names
        assert "momentum_breakout" in names

    def test_templates_empty(self, client):
        resp = client.get("/api/strategies/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []

    def test_create_template(self, client):
        template = {
            "name": "테스트 템플릿",
            "description": "테스트용",
            "strategy_type": "mean_reversion",
            "default_parameters": {"lookback_period": 20},
        }
        resp = client.post("/api/strategies/templates", json=template)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["name"] == "테스트 템플릿"


# ── GET /api/backtest/{id}/export ──


class TestExportCSV:
    @patch("app.api.backtest.run_backtest_task")
    def test_export_csv(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest", json=VALID_BACKTEST)
        job_id = resp.json()["data"]["job_id"]

        resp = client.get(f"/api/backtest/{job_id}/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]


# ── POST /api/backtest/compare ──

VALID_COMPARE = {
    "name": "전략 비교 테스트",
    "strategies": [
        {"strategy_name": "mean_reversion", "parameters": {"lookback_period": 20}},
        {"strategy_name": "momentum_breakout", "parameters": {"ma_period": 20}},
    ],
    "market": "KR",
    "symbols": ["005930"],
    "timeframe": "1d",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-06-01T00:00:00",
    "initial_capital": 10000000,
}


class TestCreateComparison:
    @patch("app.api.compare.run_backtest_task")
    def test_create_success(self, mock_task, client):
        mock_task.delay = MagicMock()

        resp = client.post("/api/backtest/compare", json=VALID_COMPARE)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "RUNNING"
        assert "job_id" in body["data"]
        # 2개 전략이므로 2번 호출
        assert mock_task.delay.call_count == 2

    @patch("app.api.compare.run_backtest_task")
    def test_create_invalid_strategy(self, mock_task, client):
        data = {
            **VALID_COMPARE,
            "strategies": [
                {"strategy_name": "nonexistent", "parameters": {}},
                {"strategy_name": "mean_reversion", "parameters": {}},
            ],
        }
        resp = client.post("/api/backtest/compare", json=data)
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "STRATEGY_NOT_FOUND"

    @patch("app.api.compare.run_backtest_task")
    def test_create_invalid_date_range(self, mock_task, client):
        data = {
            **VALID_COMPARE,
            "start_date": "2024-06-01T00:00:00",
            "end_date": "2024-01-01T00:00:00",
        }
        resp = client.post("/api/backtest/compare", json=data)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_DATE_RANGE"

    def test_create_too_few_strategies(self, client):
        data = {
            **VALID_COMPARE,
            "strategies": [{"strategy_name": "mean_reversion", "parameters": {}}],
        }
        resp = client.post("/api/backtest/compare", json=data)
        assert resp.status_code == 422  # Pydantic validation


class TestGetComparison:
    @patch("app.api.compare.run_backtest_task")
    def test_get_existing(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest/compare", json=VALID_COMPARE)
        comparison_id = resp.json()["data"]["job_id"]

        resp = client.get(f"/api/backtest/compare/{comparison_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["id"] == comparison_id
        assert body["data"]["name"] == "전략 비교 테스트"
        assert len(body["data"]["results"]) == 2

    def test_get_not_found(self, client):
        resp = client.get("/api/backtest/compare/nonexistent-id")
        assert resp.status_code == 404


class TestGetComparisonStatus:
    @patch("app.api.compare.run_backtest_task")
    def test_status(self, mock_task, client):
        mock_task.delay = MagicMock()
        resp = client.post("/api/backtest/compare", json=VALID_COMPARE)
        comparison_id = resp.json()["data"]["job_id"]

        resp = client.get(f"/api/backtest/compare/{comparison_id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] in ["PENDING", "RUNNING"]


# ── Health Check ──


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
