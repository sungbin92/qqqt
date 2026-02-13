"""DB 초기화 스크립트: 연결 대기 + Alembic 마이그레이션 실행"""

import subprocess
import sys
import time

from sqlalchemy import create_engine, text

from app.config import settings


def wait_for_db(max_retries: int = 30, delay: float = 2.0) -> None:
    """DB가 준비될 때까지 대기"""
    engine = create_engine(settings.database_url)
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"DB 연결 성공 (시도 {attempt}/{max_retries})")
            engine.dispose()
            return
        except Exception as e:
            print(f"DB 연결 대기 중... ({attempt}/{max_retries}): {e}")
            time.sleep(delay)
    engine.dispose()
    print("DB 연결 실패!")
    sys.exit(1)


def run_migrations() -> None:
    """Alembic 마이그레이션 실행"""
    print("Alembic 마이그레이션 실행 중...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"마이그레이션 실패:\n{result.stderr}")
        sys.exit(1)
    print(f"마이그레이션 완료:\n{result.stdout}")


if __name__ == "__main__":
    wait_for_db()
    run_migrations()
