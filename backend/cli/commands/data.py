"""data 명령어 (download, batch-download, presets)"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from app.config import settings
from app.data.cache import CachedDataProvider
from app.data.kis_api import KISDataProvider
from app.data.presets import get_preset, list_presets
from app.db.models import MarketType, TimeframeType
from app.db.session import SessionLocal
from app.utils.exceptions import BacktestError

app = typer.Typer(no_args_is_help=True)
console = Console()


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise typer.BadParameter(f"날짜 형식 오류: {value} (YYYY-MM-DD 필요)")


@app.command()
def download(
    symbol: str = typer.Option(..., "--symbol", help="종목 코드 (예: 005930, AAPL)"),
    market: str = typer.Option("KR", "--market", "-m", help="시장 (KR/US)"),
    start: str = typer.Option(..., "--start", help="시작일 (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="종료일 (YYYY-MM-DD)"),
    timeframe: str = typer.Option("1d", "--timeframe", "-t", help="봉 단위 (1d/1h)"),
):
    """KIS API로 시장 데이터 수집 → DB 캐시 저장"""
    start_dt = _parse_date(start)
    end_dt = _parse_date(end)

    if start_dt >= end_dt:
        console.print(Panel("[red]시작일이 종료일보다 같거나 늦습니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    market_upper = market.upper()
    if market_upper not in ("KR", "US"):
        console.print(Panel("[red]시장은 KR 또는 US만 지원합니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    market_type = MarketType.KR if market_upper == "KR" else MarketType.US
    tf = TimeframeType.D1 if timeframe == "1d" else TimeframeType.H1

    console.print(f"\n[bold cyan]데이터 수집 시작[/bold cyan]")
    console.print(f"  종목: {symbol} ({market_upper})")
    console.print(f"  기간: {start} ~ {end}")
    console.print(f"  봉: {timeframe}\n")

    asyncio.run(_download_async(symbol, market_type, tf, start_dt, end_dt))


async def _download_async(
    symbol: str,
    market: MarketType,
    timeframe: TimeframeType,
    start: datetime,
    end: datetime,
) -> None:
    provider = KISDataProvider()
    db = SessionLocal()

    try:
        cached = CachedDataProvider(provider, db)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"[green]{symbol} 데이터 수집 중...", total=1)

            df = await cached.fetch_ohlcv(symbol, market, timeframe, start, end)

            progress.update(task, completed=1)

        if df.empty:
            console.print(Panel("[yellow]수집된 데이터가 없습니다.[/yellow]", title="알림"))
        else:
            console.print(
                Panel(
                    f"[green]수집 완료: {len(df)}건[/green]\n"
                    f"  기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}",
                    title="성공",
                )
            )

    except BacktestError as e:
        console.print(Panel(f"[red]{e.message}[/red]", title=f"오류 [{e.error_code}]"))
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(Panel(f"[red]데이터 수집 실패: {e}[/red]", title="오류"))
        raise typer.Exit(code=1)
    finally:
        await provider.close()
        db.close()


@app.command("batch-download")
def batch_download(
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="종목 프리셋 (예: kospi10, mag7)"),
    symbols: Optional[str] = typer.Option(None, "--symbols", "-s", help="종목 코드 (쉼표 구분, 예: 005930,000660)"),
    market: str = typer.Option("KR", "--market", "-m", help="시장 (KR/US). --symbols 사용 시 필요"),
    start: str = typer.Option(..., "--start", help="시작일 (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="종료일 (YYYY-MM-DD)"),
    timeframe: str = typer.Option("1d", "--timeframe", "-t", help="봉 단위 (1d/1h)"),
):
    """여러 종목 데이터를 배치로 수집"""
    # 상호 배타적 옵션 검증
    if preset and symbols:
        console.print(Panel("[red]--preset과 --symbols는 동시에 사용할 수 없습니다.[/red]", title="오류"))
        raise typer.Exit(code=1)
    if not preset and not symbols:
        console.print(Panel("[red]--preset 또는 --symbols 중 하나를 지정하세요.[/red]", title="오류"))
        raise typer.Exit(code=1)

    start_dt = _parse_date(start)
    end_dt = _parse_date(end)

    if start_dt >= end_dt:
        console.print(Panel("[red]시작일이 종료일보다 같거나 늦습니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    # 종목 목록 및 시장 결정
    if preset:
        try:
            p = get_preset(preset)
        except ValueError as e:
            console.print(Panel(f"[red]{e}[/red]", title="오류"))
            raise typer.Exit(code=1)
        symbol_list = p.symbols
        market_str = p.market
    else:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        market_str = market.upper()

    if market_str not in ("KR", "US"):
        console.print(Panel("[red]시장은 KR 또는 US만 지원합니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    market_type = MarketType.KR if market_str == "KR" else MarketType.US
    tf = TimeframeType.D1 if timeframe == "1d" else TimeframeType.H1

    console.print(f"\n[bold cyan]배치 데이터 수집 시작[/bold cyan]")
    if preset:
        console.print(f"  프리셋: {preset} ({len(symbol_list)}종목)")
    console.print(f"  시장: {market_str}")
    console.print(f"  기간: {start} ~ {end}")
    console.print(f"  봉: {timeframe}\n")

    asyncio.run(_batch_download_async(symbol_list, market_type, tf, start_dt, end_dt))


async def _batch_download_async(
    symbols: List[str],
    market: MarketType,
    timeframe: TimeframeType,
    start: datetime,
    end: datetime,
) -> None:
    provider = KISDataProvider()
    db = SessionLocal()
    results = []  # (symbol, status, count, elapsed)

    try:
        cached = CachedDataProvider(provider, db)
        total_start = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            overall = progress.add_task("[bold green]전체 진행률", total=len(symbols))

            for symbol in symbols:
                sym_start = time.time()
                progress.update(overall, description=f"[bold green]{symbol} 수집 중...")

                try:
                    df = await cached.fetch_ohlcv(symbol, market, timeframe, start, end)
                    count = len(df) if not df.empty else 0
                    elapsed = time.time() - sym_start
                    results.append((symbol, "성공", count, elapsed))
                except Exception as e:
                    elapsed = time.time() - sym_start
                    results.append((symbol, f"실패: {e}", 0, elapsed))

                progress.advance(overall)

                # KIS API 레이트 리밋 고려: 종목 간 0.5초 딜레이
                await asyncio.sleep(0.5)

        total_elapsed = time.time() - total_start

        # 요약 테이블 출력
        table = Table(title="배치 다운로드 결과")
        table.add_column("종목", style="cyan")
        table.add_column("상태", style="green")
        table.add_column("건수", justify="right")
        table.add_column("소요시간", justify="right")

        success_count = 0
        fail_count = 0
        total_records = 0

        for symbol, status, count, elapsed in results:
            style = "green" if status == "성공" else "red"
            table.add_row(
                symbol,
                f"[{style}]{status}[/{style}]",
                str(count),
                f"{elapsed:.1f}s",
            )
            if status == "성공":
                success_count += 1
                total_records += count
            else:
                fail_count += 1

        console.print(table)
        console.print(
            Panel(
                f"[bold]성공: {success_count} / 실패: {fail_count} / "
                f"총 {total_records}건 / 소요시간: {total_elapsed:.1f}s[/bold]",
                title="요약",
            )
        )

    except Exception as e:
        console.print(Panel(f"[red]배치 다운로드 실패: {e}[/red]", title="오류"))
        raise typer.Exit(code=1)
    finally:
        await provider.close()
        db.close()


@app.command()
def presets():
    """등록된 종목 프리셋 목록 조회"""
    preset_list = list_presets()

    table = Table(title="종목 프리셋 목록")
    table.add_column("이름", style="cyan")
    table.add_column("설명", style="white")
    table.add_column("시장", style="yellow")
    table.add_column("종목 수", justify="right")
    table.add_column("종목", style="dim")

    for p in preset_list:
        symbols_str = ", ".join(p.symbols[:5])
        if len(p.symbols) > 5:
            symbols_str += f" 외 {len(p.symbols) - 5}개"
        table.add_row(p.name, p.description, p.market, str(len(p.symbols)), symbols_str)

    console.print(table)
