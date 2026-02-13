FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 (psycopg2-binary 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install --no-cache-dir poetry

# 의존성 먼저 복사 (Docker 캐시 활용)
COPY backend/pyproject.toml backend/poetry.lock ./

# 가상환경을 프로젝트 내부에 생성하지 않도록 설정 + 프로덕션 의존성만 설치
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# 소스 복사
COPY backend/ .
COPY scripts/ scripts/

# 로그 디렉토리 생성
RUN mkdir -p logs

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
