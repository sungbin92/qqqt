"""CLI 엔트리포인트 (Typer + Rich)"""

import typer

from cli.commands.backtest import app as backtest_app
from cli.commands.data import app as data_app
from cli.commands.optimize import app as optimize_app

app = typer.Typer(
    name="qbt",
    help="퀀트 백테스팅 시스템 CLI",
    no_args_is_help=True,
)

app.add_typer(backtest_app, name="backtest", help="백테스팅 실행/조회")
app.add_typer(data_app, name="data", help="시장 데이터 수집")
app.add_typer(optimize_app, name="optimize", help="파라미터 최적화 (Phase 5)")


if __name__ == "__main__":
    app()
