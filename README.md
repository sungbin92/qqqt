# Quant Backtest (qqqt)

퀀트 기반 주식 투자 전략을 과거 데이터로 백테스팅하는 시스템.
한국(KIS API) 및 미국 주식을 지원하며, CLI / REST API / 웹 대시보드로 사용할 수 있다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic |
| 비동기 작업 | Celery + Redis |
| 기술 지표 | pandas-ta |
| DB | PostgreSQL 15 |
| Frontend | Next.js 14, Tailwind CSS, shadcn/ui, React Query, Recharts |
| 패키지 | Poetry (backend), npm (frontend) |
| 인프라 | Docker Compose |

## 빠른 시작

### 1. Docker Compose (권장)

모든 서비스를 한 번에 실행한다.

```bash
cd docker
docker compose up -d
```

| 서비스 | 포트 | 설명 |
|--------|------|------|
| frontend | http://localhost:3000 | 웹 대시보드 |
| backend | http://localhost:8000 | REST API |
| celery-worker | - | 비동기 백테스팅 처리 |
| db (PostgreSQL) | 5433 | 데이터 저장 |
| redis | 6380 | Celery 브로커 |

### 2. 로컬 개발 환경

**사전 요구사항**: Python 3.12+, Poetry, Node.js 18+, PostgreSQL, Redis

```bash
# Backend
cd backend
cp .env.example .env    # 환경변수 설정
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload

# Celery worker (별도 터미널)
cd backend
poetry run celery -A app.worker.celery_app worker --loglevel=info

# Frontend (별도 터미널)
cd frontend
npm install
npm run dev
```

### 환경변수 (backend/.env)

```
DATABASE_URL=postgresql://postgres:1234@localhost:5432/quant_backtest
REDIS_URL=redis://localhost:6379/0
KIS_APP_KEY=<한국투자증권 앱키>
KIS_APP_SECRET=<한국투자증권 시크릿>
```

## CLI 사용법

CLI 명령어는 `qbt`로 실행한다. (`backend/` 디렉토리에서 `poetry run qbt`)

### 백테스팅 실행

```bash
# MeanReversion 전략으로 삼성전자 백테스팅
poetry run qbt backtest run \
  --strategy MeanReversion \
  --symbol 005930 \
  --market KR \
  --start 2023-01-01 \
  --end 2024-01-01 \
  --capital 10000000

# 저장된 백테스팅 목록 조회
poetry run qbt backtest list

# 백테스팅 상세 결과 조회
poetry run qbt backtest show <backtest_id>
```

### 데이터 수집

```bash
# 단일 종목 데이터 수집
poetry run qbt data download \
  --symbol 005930 \
  --market KR \
  --start 2023-01-01 \
  --end 2024-01-01

# 프리셋으로 배치 수집 (예: KOSPI 상위 10종목)
poetry run qbt data batch-download \
  --preset kospi10 \
  --start 2023-01-01 \
  --end 2024-01-01

# 종목 프리셋 목록 확인
poetry run qbt data presets
```

### 파라미터 최적화

```bash
poetry run qbt optimize run \
  --strategy MeanReversion \
  --symbol 005930 \
  --param "window:10:30:5" \
  --param "z_threshold:1.0:3.0:0.5"
```

## REST API

API 문서는 서버 실행 후 http://localhost:8000/docs (Swagger UI)에서 확인할 수 있다.

### 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스체크 |
| **백테스팅** | | |
| `POST` | `/api/backtest` | 백테스팅 생성 (비동기) |
| `GET` | `/api/backtest` | 백테스팅 목록 조회 |
| `GET` | `/api/backtest/{id}` | 백테스팅 결과 조회 |
| `GET` | `/api/backtest/{id}/status` | 실행 상태 확인 |
| `GET` | `/api/backtest/{id}/export` | 결과 내보내기 |
| `DELETE` | `/api/backtest/{id}` | 백테스팅 삭제 |
| **전략 비교** | | |
| `POST` | `/api/backtest/compare` | 다중 전략 비교 실행 |
| `GET` | `/api/backtest/compare/{id}` | 비교 결과 조회 |
| `GET` | `/api/backtest/compare/{id}/status` | 비교 상태 확인 |
| **전략** | | |
| `GET` | `/api/strategies` | 전략 목록 |
| `GET` | `/api/strategies/templates` | 전략 템플릿 목록 |
| `POST` | `/api/strategies/templates` | 전략 템플릿 저장 |
| **데이터** | | |
| `GET` | `/api/data/symbols` | 종목 검색 |
| `GET` | `/api/data/ohlcv` | OHLCV 데이터 조회 |
| **최적화** | | |
| `POST` | `/api/optimize` | 파라미터 최적화 실행 |
| `GET` | `/api/optimize/{id}` | 최적화 결과 조회 |
| `GET` | `/api/optimize/{id}/status` | 최적화 상태 확인 |

## 웹 대시보드

| 페이지 | 경로 | 설명 |
|--------|------|------|
| 대시보드 | `/dashboard` | 최근 백테스팅 요약 |
| 백테스팅 목록 | `/backtest` | 실행된 백테스팅 관리 |
| 백테스팅 생성 | `/backtest/new` | 전략/종목/기간 설정 후 실행 |
| 결과 상세 | `/backtest/[id]` | 성과 지표, 수익률 차트, 거래 내역 |
| 전략 관리 | `/strategies` | 전략 목록 및 템플릿 |
| 전략 비교 | `/compare` | 다중 전략 동시 비교 차트 |
| 파라미터 최적화 | `/optimize` | Grid Search 기반 최적화 |

## 구현된 전략

| 전략 | 클래스 | 설명 |
|------|--------|------|
| 평균 회귀 | `MeanReversionStrategy` | 볼린저 밴드 기반, 가격이 평균에서 벗어나면 진입 |
| 모멘텀 돌파 | `MomentumBreakoutStrategy` | 가격 모멘텀과 돌파 신호로 추세 추종 |

## 테스트

```bash
cd backend
poetry run pytest                      # 전체 테스트
poetry run pytest tests/unit/          # 단위 테스트
poetry run pytest tests/integration/   # 통합 테스트
poetry run pytest --cov=app            # 커버리지 포함
```

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── config.py            # Settings, 시장 설정
│   ├── api/                 # REST API 라우트
│   ├── engine/              # 백테스팅 엔진 (broker, portfolio, order, backtest)
│   ├── strategies/          # 투자 전략 (base, mean_reversion, momentum_breakout)
│   ├── indicators/          # 기술적 지표 (pandas-ta 래핑)
│   ├── data/                # 데이터 수집 (KIS API, 캐시)
│   ├── analytics/           # 성과 분석 (수익률, 리스크, 리포트)
│   ├── optimizer/           # 파라미터 최적화 (Grid Search)
│   ├── worker/              # Celery 비동기 워커
│   ├── db/                  # SQLAlchemy 모델 + 세션
│   └── utils/               # 로거, 예외, 응답 포맷
├── cli/                     # Typer CLI (qbt)
├── tests/                   # pytest (unit, integration, fixtures)
├── alembic/                 # DB 마이그레이션
└── pyproject.toml

frontend/
├── app/                     # Next.js App Router 페이지
├── components/              # React 컴포넌트
└── package.json

docker/
├── docker-compose.yml       # 전체 서비스 구성
├── backend.Dockerfile
└── frontend.Dockerfile
```
