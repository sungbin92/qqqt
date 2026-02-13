# Claude Code 작업 명령 리스트

> 각 명령은 이전 단계가 완료되고 테스트 통과를 확인한 후 실행한다.
> 모든 명령의 앞에 "SPEC.md를 참고해서" 를 붙인다.
> 각 단계 완료 후 `poetry run pytest`로 테스트 통과 확인.

---

## Phase 1: 핵심 엔진 (2주)

### 1-1. 프로젝트 초기 설정

```
SPEC.md를 읽어줘.
이 스펙을 기반으로 프로젝트 초기 설정을 해줘.

1. backend/ 디렉토리에 Poetry 프로젝트 생성 (pyproject.toml은 SPEC의 내용 그대로)
2. SPEC의 파일 구조대로 backend/app/ 하위 디렉토리와 __init__.py 생성
3. .env.example 생성
4. app/config.py 구현 (Settings, MarketConfig, MARKET_CONFIGS)
5. app/utils/logger.py 구현 (기본 로깅 설정)
6. app/utils/exceptions.py 구현 (커스텀 예외 클래스 — SPEC 섹션 9의 에러 코드 기반)
7. app/utils/response.py 구현 (ApiResponse 래퍼 헬퍼)

poetry install까지 실행해서 의존성 설치 확인해줘.
```

### 1-2. DB 모델 + 마이그레이션

```
SPEC.md 섹션 4의 데이터 모델을 참고해서:

1. app/db/session.py 구현 (SQLAlchemy async engine + session 팩토리)
2. app/db/models.py 구현 (Backtest, Trade, StrategyTemplate, MarketData, OptimizationResult + 모든 Enum)
3. Alembic 초기 설정 (alembic init alembic)
4. alembic/env.py에서 models.py의 Base.metadata를 참조하도록 설정
5. 초기 마이그레이션 생성 및 적용

로컬 PostgreSQL에 연결해서 테이블 생성까지 확인해줘.
DB 연결 정보는 .env 파일 참고.
```

### 1-3. Broker 클래스 (수수료/슬리피지/포지션 한도)

```
SPEC.md의 Broker 구현 가이드와 비즈니스 로직 섹션 8을 참고해서:

1. app/engine/broker.py 구현
   - MarketConfig 기반 수수료 계산 (KR/US 분기)
   - 슬리피지 적용 (일봉/시간봉 분기)
   - 다음 봉 시가 기준 체결가 계산 (calculate_fill_price)
   - 투자 비율 → 실제 수량 변환 (calculate_quantity)
   - 포지션 한도 검증 (validate_order)
     - 종목당 최대 40%
     - 최소 잔여 현금 5%
     - 최소 주문 금액
2. tests/unit/test_broker.py 작성
   - KR 시장 수수료 계산 테스트
   - US 시장 수수료 계산 테스트 (최소 수수료 $1 적용 케이스 포함)
   - 슬리피지 매수/매도 방향 검증
   - 포지션 한도 초과 시 수량 축소 검증
   - 현금 부족 시 주문 거부 검증

테스트 통과 확인해줘.
```

### 1-4. Portfolio + Position 클래스

```
SPEC.md를 참고해서 포트폴리오 관리 클래스를 구현해줘.

1. app/engine/position.py
   - Position 데이터 클래스 (symbol, quantity, avg_price, market_value)
   - 포지션 추가/부분매도 시 평균단가 재계산
2. app/engine/portfolio.py
   - Portfolio 클래스
     - cash: 현금 잔고
     - positions: Dict[str, Position]
     - equity: 총 평가액 (cash + 모든 포지션 시가평가)
     - get_position(symbol) → Position | None
     - update_market_prices(prices: Dict[str, float]) → 시가평가 갱신
     - execute_buy(symbol, quantity, fill_price, commission)
     - execute_sell(symbol, quantity, fill_price, commission)
     - get_position_weight(symbol) → 해당 종목이 포트폴리오에서 차지하는 비율
3. tests/unit/test_portfolio.py
   - 초기 현금 설정 검증
   - 매수 후 포지션/현금 변화 검증
   - 매도 후 현금 회수 + 수수료 차감 검증
   - 부분 매도 검증
   - 평가액(equity) 계산 검증
   - 존재하지 않는 종목 매도 시 에러 검증

테스트 통과 확인해줘.
```

### 1-5. Order + BacktestEngine

```
SPEC.md 섹션 8의 "주문 실행 파이프라인"을 참고해서:

1. app/engine/order.py
   - PendingOrder 데이터 클래스 (symbol, side, weight, reason)
   - FilledOrder 데이터 클래스 (signal_price, signal_date, fill_price, fill_date, quantity, commission)
2. app/engine/backtest.py — BacktestEngine 클래스
   - 입력: Strategy, DataFrame(OHLCV), Broker, initial_capital
   - 메인 루프:
     a. 봉(t) 완성 → strategy.on_bar() 호출 → PendingOrder 리스트 수집
     b. 다음 봉(t+1) 도착 → Broker가 체결가 결정
     c. Broker.calculate_quantity()로 수량 확정
     d. Broker.validate_order()로 검증
     e. Portfolio.execute_buy/sell() 실행
     f. equity_curve 기록
   - 결과 반환: trades 리스트, equity_curve, 성과 지표
   - 진행률 콜백 지원 (Celery 연동용): on_progress(percent: int)
3. tests/unit/test_engine.py
   - 단순 "매봉 매수" 전략으로 엔진 동작 검증
   - 시그널(t봉 종가) → 체결(t+1봉 시가) 타이밍 검증
   - 수수료/슬리피지가 반영된 PnL 검증
   - 데이터가 2봉 미만일 때 엣지 케이스

테스트 통과 확인해줘.
```

### 1-6. Strategy 베이스 + 예제 전략 1 (평균회귀)

```
SPEC.md의 전략 구현 가이드를 참고해서:

1. app/strategies/base.py
   - Strategy ABC (SPEC 그대로)
   - _state를 종목별로 분리하는 구조
2. app/strategies/mean_reversion.py
   - MeanReversionStrategy (SPEC 그대로)
   - 파라미터: lookback_period, entry_threshold, exit_threshold, position_weight
3. tests/unit/test_strategy.py
   - 가격이 평균 대비 2σ 이하일 때 매수 시그널 생성 검증
   - 가격이 평균으로 회귀했을 때 매도 시그널 검증
   - lookback 기간 미달 시 시그널 없음 검증
   - 표준편차 0일 때 시그널 없음 검증
   - 다중 종목에서 종목별 독립 상태 유지 검증
4. tests/fixtures/sample_ohlcv.csv 생성 (삼성전자 3개월 일봉 샘플 — 임의 데이터로 생성)

테스트 통과 확인해줘.
```

### 1-7. 성과 분석 모듈

```
SPEC.md의 PerformanceMetrics 구현 가이드를 참고해서:

1. app/analytics/performance.py (SPEC 그대로)
   - calculate_returns, total_return, annual_return
   - sharpe_ratio, sortino_ratio
   - max_drawdown
   - win_rate, profit_factor
   - max_consecutive (연속 승/패)
2. app/analytics/risk.py
   - calmar_ratio (annual_return / max_drawdown)
   - 일별 VaR (Value at Risk, 95% 신뢰구간)
3. tests/unit/test_performance.py
   - 알려진 값으로 각 지표 계산 검증 (수동 계산 결과와 비교)
   - 엣지 케이스: 거래 0건, equity 변동 없음, 전부 수익, 전부 손실
   - max_consecutive 검증 (연속 3승 2패 1승 → max_consecutive_wins=3)

테스트 통과 확인해줘.
```

### 1-8. Phase 1 통합 테스트

```
Phase 1에서 만든 모든 모듈을 연결해서 end-to-end 통합 테스트를 작성해줘.

tests/integration/test_backtest_e2e.py:
1. sample_ohlcv.csv 로드 → DataFrame 변환
2. MeanReversionStrategy + Broker(KR, 일봉) + BacktestEngine 조합
3. 백테스팅 실행
4. 검증:
   - trades 리스트가 비어있지 않음
   - 모든 trade의 fill_date가 signal_date보다 이후
   - equity_curve 길이 == 데이터 봉 수
   - PerformanceMetrics로 계산한 지표가 NaN/None이 아님
   - 최종 equity + 잔여 cash == portfolio.equity (정합성)
5. US 시장 설정으로도 동일 테스트 (수수료 체계 변경 확인)

전체 테스트 스위트 실행: poetry run pytest --cov=app
커버리지 리포트 확인해줘.
```

---

## Phase 2: 데이터 수집 + CLI (1주)

### 2-1. 데이터 프로바이더 인터페이스 + KIS API (국내)

```
SPEC.md를 참고해서 데이터 수집 모듈을 구현해줘.

1. app/data/provider.py
   - DataProvider ABC
     - async fetch_ohlcv(symbol, market, timeframe, start, end) → pd.DataFrame
     - async search_symbols(market, query) → List[SymbolInfo]
2. app/data/kis_api.py — KISDataProvider(DataProvider)
   - 한국투자증권 API 클라이언트 (httpx 비동기)
   - 토큰 발급 + 자동 갱신
   - 국내 주식 일봉/시간봉 조회
   - Rate Limit 준수: 초당 20건 제한 (asyncio.Semaphore)
   - 에러 시 3회 재시도 (exponential backoff)
   - API 응답 → OHLCV DataFrame 변환
3. app/data/cache.py
   - MarketData 테이블 기반 캐싱
   - fetch 전 캐시 확인 (fetched_at + TTL로 만료 판단)
   - 캐시 미스 시 KIS API 호출 → DB 저장 (upsert)
4. tests/integration/test_data_provider.py
   - KIS API Mock (respx 사용)
   - 캐시 히트/미스 동작 검증
   - Rate Limit 재시도 로직 검증

주의: KIS API의 정확한 엔드포인트/파라미터는 https://apiportal.koreainvestment.com 문서를
참고해야 합니다. 문서 확인이 어렵다면 인터페이스만 구현하고 실제 API 호출 부분은
TODO 주석으로 남겨줘.

테스트 통과 확인해줘.
```

### 2-2. KIS API (미국 주식)

```
SPEC.md 섹션 10의 한국투자증권 API 미국 주식 관련 내용을 참고해서:

app/data/kis_api.py에 미국 주식 시세 조회 기능을 추가해줘.

1. 해외주식 기간별 시세 API 연동
   - 국내와 엔드포인트/파라미터가 다르므로 market별 분기 처리
   - 미국 주식 심볼 형식 처리 (예: AAPL, MSFT)
2. 해외주식 종목 검색 (search_symbols에서 market="US" 분기)
3. 응답 파싱: 미국 주식 OHLCV → 동일한 DataFrame 형식으로 통일
4. 테스트: respx로 미국 주식 API 응답 Mock 후 검증

마찬가지로 KIS 해외주식 API의 정확한 스펙은 공식 문서 참고 필요.
확인이 어려운 부분은 TODO 주석으로 남겨줘.

테스트 통과 확인해줘.
```

### 2-3. CLI 구현

```
SPEC.md 섹션 7 CLI 요구사항을 참고해서:

1. cli/main.py — Typer 앱 엔트리포인트
2. cli/commands/backtest.py
   - backtest run: 전략/종목/기간/자본금 옵션 → BacktestEngine 직접 실행 → Rich Table로 결과 출력
   - backtest list: DB에서 최근 백테스팅 목록 조회 → Rich Table
   - backtest show <id>: 상세 결과 출력 (성과 지표 + 거래 요약)
3. cli/commands/data.py
   - data download: 종목/기간 지정 → KIS API로 데이터 수집 → DB 캐시 저장
   - Rich Progress bar로 진행률 표시
4. cli/commands/optimize.py
   - (placeholder만 — Phase 5에서 구현)
5. pyproject.toml에 CLI 스크립트 엔트리포인트 등록:
   [tool.poetry.scripts]
   qbt = "cli.main:app"
   → 이후 `poetry run qbt backtest run ...` 으로 실행 가능

테스트: CLI가 --help 출력되는지, 샘플 데이터로 backtest run이 동작하는지 확인해줘.
```

### 2-4. 예제 전략 2 (모멘텀 돌파)

```
SPEC.md의 MomentumBreakoutStrategy 구현 가이드를 참고해서:

1. app/strategies/momentum_breakout.py
   - 이동평균 돌파 + 거래량 증가 조건 매수
   - 손절/익절 기반 매도
   - 다중 종목 지원 (_state 종목별 분리)
   - 파라미터: ma_period, volume_ma_period, volume_threshold, stop_loss_pct, take_profit_pct, position_weight
2. tests/unit/test_momentum_strategy.py
   - 이동평균 돌파 + 거래량 급증 시 매수 시그널 검증
   - 손절 조건 (-5%) 시 매도 시그널 검증
   - 익절 조건 (+15%) 시 매도 시그널 검증
   - 거래량 조건 미달 시 매수 안 함 검증
3. app/strategies/__init__.py에 전략 레지스트리 구현
   - STRATEGY_REGISTRY: Dict[str, Type[Strategy]]
   - get_strategy(name, parameters) → Strategy 인스턴스

테스트 통과 확인해줘.
```

---

## Phase 3: 비동기 처리 + API (1주)

### 3-1. Celery 워커 설정

```
SPEC.md를 참고해서 Celery 비동기 작업 처리를 구현해줘.

1. app/worker/celery_app.py
   - Celery 앱 설정 (Redis broker)
   - 기본 설정: task_serializer='json', result_backend='redis'
2. app/worker/tasks.py
   - run_backtest_task(backtest_id: str)
     a. DB에서 Backtest 레코드 조회
     b. job_status → RUNNING 업데이트
     c. 데이터 수집 (캐시 → KIS API)
     d. BacktestEngine 실행 (on_progress 콜백으로 DB progress 업데이트)
     e. 성과 지표 계산 → DB 업데이트
     f. trades, equity_curve_data 저장
     g. job_status → COMPLETED
     h. 예외 발생 시: job_status → FAILED, job_error 저장
   - run_optimization_task(optimization_id: str)
     - (placeholder — Phase 5에서 구현)
3. docker-compose에 Redis 서비스 추가

Celery 워커가 정상 기동하는지 확인해줘:
celery -A app.worker.celery_app worker --loglevel=info
```

### 3-2. FastAPI 엔드포인트

```
SPEC.md 섹션 5 API 엔드포인트를 참고해서:

1. app/api/router.py — 라우터 통합
2. app/api/backtest.py
   - POST /api/backtest → Backtest DB 레코드 생성 + Celery task 발행 → JobResponse 반환
   - GET /api/backtest → 페이지네이션 목록 (BacktestSummary[])
   - GET /api/backtest/{id} → BacktestDetail (trades, equity_curve 포함)
   - GET /api/backtest/{id}/status → { status, progress }
   - DELETE /api/backtest/{id}
   - GET /api/backtest/{id}/export → StreamingResponse CSV
3. app/api/strategies.py
   - GET /api/strategies → STRATEGY_REGISTRY에서 목록 반환
   - GET /api/strategies/templates → DB 조회
   - POST /api/strategies/templates → 템플릿 저장
4. app/api/data.py
   - GET /api/data/symbols → 종목 검색
   - GET /api/data/ohlcv → 시세 조회
5. app/api/schemas.py — SPEC의 Pydantic 스키마 전부 구현
6. app/main.py — FastAPI 앱 + 라우터 등록 + CORS 설정

모든 응답은 ApiResponse 래퍼를 사용해줘.
```

### 3-3. API 통합 테스트

```
FastAPI TestClient로 API 통합 테스트를 작성해줘.

tests/integration/test_api.py:
1. POST /api/backtest
   - 정상 요청 → 200 + JobResponse (job_id, status=PENDING)
   - 잘못된 날짜 범위 → 400 + INVALID_DATE_RANGE
   - 존재하지 않는 전략 → 404 + STRATEGY_NOT_FOUND
   - 최소 자본금 미달 → 400 + INSUFFICIENT_CAPITAL
2. GET /api/backtest → 목록 반환 + 페이지네이션 meta 검증
3. GET /api/backtest/{id} → 존재하는 ID / 없는 ID
4. DELETE /api/backtest/{id} → 삭제 확인
5. GET /api/strategies → 전략 목록에 MeanReversion, MomentumBreakout 포함

DB는 테스트용 SQLite in-memory 또는 별도 test DB 사용.
Celery task는 mock 처리 (task.delay → 직접 실행).

테스트 통과 확인해줘.
```

### 3-4. Docker Compose

```
SPEC.md 파일 구조의 docker/ 디렉토리를 참고해서:

1. docker/backend.Dockerfile
   - Python 3.11-slim 베이스
   - Poetry로 의존성 설치
   - uvicorn으로 FastAPI 실행
2. docker/docker-compose.yml
   - services: backend, celery-worker, postgres, redis
   - backend: FastAPI (포트 8000)
   - celery-worker: Celery 워커 (같은 이미지, 다른 커맨드)
   - postgres: 15-alpine (볼륨 마운트)
   - redis: 7-alpine
   - .env 파일 참조
3. scripts/init_db.py — Alembic 마이그레이션 자동 실행 스크립트

docker-compose up으로 전체 서비스가 기동되는지 확인해줘.
```

---

## Phase 4: 웹 대시보드 (2주)

### 4-1. Next.js 프로젝트 설정

```
SPEC.md를 참고해서 프론트엔드 프로젝트를 설정해줘.

1. frontend/ 디렉토리에 Next.js 14 (App Router) 프로젝트 생성 (pnpm)
2. Tailwind CSS + shadcn/ui 설정
3. lib/api-client.ts 구현
   - Backend API 베이스 클라이언트 (fetch 래퍼)
   - ApiResponse 타입 처리
   - 에러 핸들링
4. lib/types.ts — SPEC의 Pydantic 스키마에 대응하는 TypeScript 타입 전부 정의
   - BacktestCreate, BacktestSummary, BacktestDetail
   - TradeResponse, JobResponse, ApiResponse 등
5. app/layout.tsx — 기본 레이아웃 (사이드바 + 상단 네비게이션)
6. React Query (TanStack Query) Provider 설정

pnpm dev로 개발 서버가 정상 기동되는지 확인해줘.
```

### 4-2. 대시보드 + 백테스팅 목록 페이지

```
SPEC.md 섹션 7 Web Dashboard 요구사항을 참고해서:

1. app/dashboard/page.tsx
   - 최근 백테스팅 5개 요약 카드 (이름, 전략, 수익률, 상태)
   - 실행 중인 작업이 있으면 진행률 표시
   - "새 백테스팅" 버튼 → /backtest/new 이동
2. app/backtest/page.tsx
   - 백테스팅 목록 테이블 (페이지네이션)
   - 컬럼: 이름, 전략, 시장, 수익률, 샤프, MDD, 상태, 생성일
   - 상태별 뱃지 색상 (PENDING: 회색, RUNNING: 파랑, COMPLETED: 초록, FAILED: 빨강)
   - 행 클릭 → /backtest/{id} 이동
   - 삭제 버튼 (확인 다이얼로그)
3. components/JobStatusBanner.tsx
   - RUNNING 상태일 때 프로그레스 바 + 자동 폴링 (3초 간격)

React Query로 서버 상태 관리. 로딩/에러 상태 처리 포함해줘.
```

### 4-3. 백테스팅 생성 폼

```
SPEC.md를 참고해서 백테스팅 생성 폼을 구현해줘.

app/backtest/new/page.tsx + components/BacktestForm.tsx:
1. 폼 필드:
   - 이름 (text)
   - 설명 (textarea, 선택)
   - 전략 선택 (GET /api/strategies에서 목록 로드 → select)
   - 전략 파라미터 (선택한 전략에 따라 동적 필드 렌더링)
   - 시장 (KR / US 라디오)
   - 종목 코드 (콤마 구분 입력 또는 검색 자동완성)
   - 타임프레임 (1h / 1d 라디오)
   - 시작일 / 종료일 (date picker)
   - 초기 자본금 (number)
2. 클라이언트 유효성 검증:
   - 시작일 < 종료일
   - 초기 자본금 > 0
   - 종목 1개 이상
3. 제출 → POST /api/backtest → 성공 시 /backtest/{id} 페이지로 이동
4. components/StrategySelector.tsx — 전략 선택 + 파라미터 폼 동적 생성

shadcn/ui 컴포넌트 활용해줘.
```

### 4-4. 백테스팅 결과 상세 페이지

```
SPEC.md를 참고해서 백테스팅 결과 상세 페이지를 구현해줘.

app/backtest/[id]/page.tsx:
1. 작업 상태에 따른 분기:
   - PENDING/RUNNING: JobStatusBanner (프로그레스 바 + 3초 폴링)
   - FAILED: 에러 메시지 표시
   - COMPLETED: 아래 결과 화면 표시
2. components/ResultsCard.tsx — 성과 지표 카드 그리드
   - 총 수익률, 연환산 수익률, 샤프 비율, 소르티노 비율
   - MDD, 승률, Profit Factor
   - 총 거래 수, 최대 연속 승/패
   - 양수는 초록, 음수는 빨강 색상
3. components/charts/EquityCurveChart.tsx — Recharts 라인 차트
   - equity_curve_data를 시계열로 표시
   - 초기 자본금 기준선 표시
4. components/charts/DrawdownChart.tsx — Recharts 영역 차트 (빨간색)
5. components/charts/TradeDistribution.tsx — PnL 분포 히스토그램
6. components/TradesTable.tsx — 거래 내역 테이블
   - 컬럼: 종목, 방향, 수량, 시그널가, 체결가, 청산가, PnL, 보유일
   - 정렬/페이지네이션
7. CSV 다운로드 버튼 → GET /api/backtest/{id}/export

Recharts로 차트 구현하고, 반응형 처리해줘.
```

### 4-5. 전략 관리 페이지

```
app/strategies/page.tsx:
1. 사용 가능한 전략 목록 (GET /api/strategies)
   - 전략 이름, 설명, 기본 파라미터 표시
2. 저장된 템플릿 목록 (GET /api/strategies/templates)
   - 템플릿 이름, 전략 타입, 저장된 파라미터
   - "이 템플릿으로 백테스팅" 버튼 → /backtest/new에 파라미터 프리필
3. 새 템플릿 저장 다이얼로그

간단하게 구현해줘. 핵심은 백테스팅 생성 시 템플릿을 불러올 수 있는 것.
```

### 4-6. 프론트엔드 Docker + 통합

```
1. docker/frontend.Dockerfile
   - Node.js 20-alpine 베이스
   - pnpm으로 의존성 설치 + 빌드
   - Next.js standalone 모드 실행
2. docker-compose.yml에 frontend 서비스 추가 (포트 3000)
   - backend 의존
   - 환경변수: NEXT_PUBLIC_API_URL=http://backend:8000
3. 전체 docker-compose up으로 프론트엔드 ↔ 백엔드 연동 확인

브라우저에서 http://localhost:3000 접속해서 동작 확인해줘.
```

---

## Phase 5: 고급 기능 (1-2주, 선택)

### 5-1. 파라미터 최적화 (Grid Search)

```
SPEC.md를 참고해서 파라미터 최적화를 구현해줘.

1. app/optimizer/grid_search.py
   - parameter_ranges → 모든 조합 생성
   - 조합 수 > 10,000 이면 에러 반환
   - 각 조합으로 BacktestEngine 실행
   - optimization_metric 기준 정렬 → 상위 10개 저장
2. app/worker/tasks.py에 run_optimization_task 구현
   - DB에서 OptimizationResult 조회
   - Grid Search 실행 (진행률 업데이트)
   - 결과 저장
3. app/api/optimize.py
   - POST /api/optimize → 작업 생성 + Celery task
   - GET /api/optimize/{id} → 결과 조회
   - GET /api/optimize/{id}/status → 진행률
4. 프론트엔드 app/optimize/page.tsx
   - 파라미터 범위 입력 폼 (min, max, step)
   - 조합 수 실시간 표시 + 10,000 초과 경고
   - 결과: 상위 10개 파라미터 + 지표 테이블
5. tests/unit/test_optimizer.py
   - 조합 생성 검증
   - 최대 조합 수 초과 에러 검증
   - 상위 N개 선택 검증

테스트 통과 확인해줘.
```

### 5-2. 다중 전략 비교

```
동일 조건에서 여러 전략을 동시 실행하고 비교하는 기능을 구현해줘.

1. app/api/backtest.py에 POST /api/backtest/compare 추가
   - 요청: { strategies: [{name, parameters}, ...], market, symbols, timeframe, start, end, capital }
   - 각 전략별 Celery task 생성
   - 모든 task 완료 후 비교 데이터 반환
2. 프론트엔드 비교 페이지 또는 모달
   - 전략별 성과 지표 비교 테이블
   - 자산 곡선 오버레이 차트 (같은 차트에 여러 전략)
   - 리스크/리턴 스캐터 플롯

기본적인 구조만 잡고, 디테일은 이후 개선해줘.
```

---

## 기타 유틸리티

### README.md

```
프로젝트 전체가 완성되면 README.md를 작성해줘.

포함 내용:
1. 프로젝트 소개 (한 줄 요약)
2. 기술 스택
3. 로컬 개발 환경 설정 (Prerequisites, 설치, 실행)
   - Poetry, Node.js, PostgreSQL, Redis 설치
   - .env 설정
   - DB 마이그레이션
   - 백엔드/프론트엔드/Celery 워커 실행 방법
4. Docker로 실행하는 방법
5. CLI 사용법 (주요 명령어 예시)
6. 구현된 전략 설명
7. 프로젝트 구조 요약
```
