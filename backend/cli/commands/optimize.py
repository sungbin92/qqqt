"""optimize 명령어 (Phase 5에서 구현)"""

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def run(
    strategy: str = typer.Option(..., "--strategy", "-s", help="전략 이름"),
    param: list[str] = typer.Option([], "--param", help="파라미터 범위 (name:min:max:step)"),
    symbol: str = typer.Option(..., "--symbol", help="종목 코드"),
    market: str = typer.Option("KR", "--market", "-m", help="시장 (KR/US)"),
):
    """파라미터 최적화 실행 (Phase 5에서 구현 예정)"""
    console.print(
        Panel(
            "[yellow]파라미터 최적화는 Phase 5에서 구현 예정입니다.[/yellow]",
            title="미구현",
        )
    )
    raise typer.Exit(code=0)
