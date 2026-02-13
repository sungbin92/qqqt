# 주식 자동투자 백테스팅 시스템

## 프로젝트 개요
퀀트 기반 주식 투자 전략을 과거 데이터로 백테스팅하는 시스템.
상세 스펙: `spec.md` / 단계별 명령: `command.md`

## 기술 스택
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, Celery+Redis
- **지표**: `pandas-ta` (TA-Lib 대신, C 의존성 없음)
- **DB**: PostgreSQL (Docker `docker-db-1` 컨테이너, `postgres/1234`)
- **패키지**: Poetry (backend/ 디렉토리에서 실행)
- **Frontend**: Next.js 14, Tailwind, shadcn/ui (Phase 4)

## 작업 디렉토리
```
backend/           ← Poetry 프로젝트 루트 (여기서 poetry run 실행)
├── app/           ← Python 패키지 루트
│   ├── config.py          Settings, MarketConfig, MARKET_CONFIGS
│   ├── api/               FastAPI 라우트
│   ├── engine/            백테스팅 엔진 (broker, portfolio, position, order, backtest)
│   ├── strategies/        전략 (base, mean_reversion, momentum_breakout)
│   ├── indicators/        기술적 지표 (pandas-ta 래핑)
│   ├── data/              데이터 수집 (KIS API, cache)
│   ├── analytics/         성과 분석 (performance, risk, report)
│   ├── optimizer/         파라미터 최적화
│   ├── worker/            Celery 워커
│   ├── db/                SQLAlchemy 모델 + 세션
│   └── utils/             logger, exceptions, response
├── cli/                   Typer CLI
├── tests/                 pytest (unit/, integration/, fixtures/)
├── alembic/               DB 마이그레이션
├── .env                   환경변수 (DB: postgresql://postgres:1234@localhost:5432/quant_backtest)
└── pyproject.toml
```

## 구현 진행 상황

### Phase 1: 핵심 엔진
| 단계 | 설명 | 상태 |
|------|------|------|
| 1-1 | 프로젝트 초기 설정 (디렉토리, config, utils, poetry install) | ✅ 완료 |
| 1-2 | DB 모델 + Alembic 마이그레이션 | ✅ 완료 |
| 1-3 | Broker 클래스 (수수료/슬리피지/포지션 한도) + 테스트 | ✅ 완료 |
| 1-4 | Portfolio + Position 클래스 + 테스트 | ✅ 완료 |
| 1-5 | Order + BacktestEngine + 테스트 | ✅ 완료 |
| 1-6 | Strategy 베이스 + MeanReversion 전략 + 테스트 | ✅ 완료 |
| 1-7 | 성과 분석 모듈 (PerformanceMetrics) + 테스트 | ✅ 완료 |
| 1-8 | Phase 1 통합 테스트 (E2E) | ✅ 완료 |

### Phase 2: 데이터 수집 + CLI
| 단계 | 설명 | 상태 |
|------|------|------|
| 2-1 | 데이터 프로바이더 인터페이스 + KIS API (국내) + 캐시 + 테스트 | ✅ 완료 |
| 2-2 | KIS API (미국 주식) + 테스트 | ✅ 완료 |
| 2-3 | CLI 구현 (Typer + Rich) | ✅ 완료 |
| 2-4 | 예제 전략 2 (모멘텀 돌파) + 전략 레지스트리 | ✅ 완료 |

### Phase 3: 비동기 처리 + API
| 단계 | 설명 | 상태 |
|------|------|------|
| 3-1 | Celery 워커 설정 (Redis broker, run_backtest_task) | ✅ 완료 |
| 3-2 | FastAPI 엔드포인트 (백테스팅/전략/데이터 API + Pydantic 스키마) | ✅ 완료 |
| 3-3 | API 통합 테스트 (TestClient, Celery mock) | ✅ 완료 |
| 3-4 | Docker Compose (backend + celery-worker + postgres + redis) | ✅ 완료 |

### Phase 4: 웹 대시보드
| 단계 | 설명 | 상태 |
|------|------|------|
| 4-1 | Next.js 프로젝트 설정 (Tailwind, shadcn/ui, React Query) | ✅ 완료 |
| 4-2 | 대시보드 + 백테스팅 목록 페이지 | ✅ 완료 |
| 4-3 | 백테스팅 생성 폼 (전략 선택 + 동적 파라미터) | ✅ 완료 |
| 4-4 | 백테스팅 결과 상세 페이지 (성과 카드 + 차트 + 거래 테이블) | ✅ 완료 |
| 4-5 | 전략 관리 페이지 (전략 목록 + 템플릿) | ✅ 완료 |
| 4-6 | 프론트엔드 Docker + 통합 | ✅ 완료 |

### Phase 5: 고급 기능 (선택)
| 단계 | 설명 | 상태 |
|------|------|------|
| 5-1 | 파라미터 최적화 (Grid Search + API + 프론트엔드) | ✅ 완료 |
| 5-2 | 다중 전략 비교 (동시 실행 + 비교 차트) | ✅ 완료 |

## 작업 규칙

### 새 대화에서 이어서 작업할 때
1. 이 파일의 "구현 진행 상황" 표에서 다음 ⬜ 항목 확인
2. `command.md`에서 해당 단계 명령 읽기
3. `spec.md`에서 관련 섹션만 참조 (전체를 다시 읽지 않음)
4. 구현 → 테스트 → 통과 확인 → 이 파일 상태 업데이트

### 코딩 컨벤션
- 포맷: Black (line-length=100), Ruff 린터
- 테스트: `poetry run pytest` (backend/ 에서 실행)
- DB 접근: `docker exec docker-db-1 psql -U postgres`
- 모든 코드는 `spec.md`의 구현 가이드 코드를 기반으로 작성
- 각 단계 완료 후 반드시 `poetry run pytest`로 전체 테스트 통과 확인

### spec 대비 변경사항 (유지해야 함)
- `pandas-ta`: `^0.3.14b1` → `>=0.4.67b0` (PyPI에 0.3.x 없음)
- Python: `^3.11` → `^3.12` (pandas-ta가 3.12+ 요구)
- `pyproject.toml`에 `package-mode = false` (Poetry 2.x)
- 버전 핀 `^` → `>=` (Python 3.13 호환)
- Settings의 `class Config` → `model_config = {"env_file": ".env"}` (Pydantic v2)
