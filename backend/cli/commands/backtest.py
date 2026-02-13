"""backtest 명령어 (run / list / show)"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.analytics.performance import PerformanceMetrics
from app.config import MARKET_CONFIGS
from app.db.models import MarketType, TimeframeType
from app.engine.backtest import BacktestEngine
from app.engine.broker import Broker
from app.engine.order import FilledOrder, OrderSide
from app.data.cache import CachedDataProvider
from app.data.kis_api import KISDataProvider
from app.db.session import SessionLocal
from app.strategies import STRATEGY_REGISTRY, get_strategy
from app.utils.exceptions import BacktestError

app = typer.Typer(no_args_is_help=True)
console = Console()

# 종목 프리셋
SYMBOL_PRESETS: Dict[str, Dict] = {
    "kospi10": {
        "market": "KR",
        "symbols": [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "373220",  # LG에너지솔루션
            "207940",  # 삼성바이오로직스
            "005490",  # POSCO홀딩스
            "006400",  # 삼성SDI
            "051910",  # LG화학
            "003670",  # 포스코퓨처엠
            "035420",  # NAVER
            "000270",  # 기아
        ],
    },
    "mag7": {
        "market": "US",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
    },
}


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise typer.BadParameter(f"날짜 형식 오류: {value} (YYYY-MM-DD 필요)")


def _generate_sample_data(
    symbol: str, start: datetime, end: datetime
) -> pd.DataFrame:
    """테스트/데모용 샘플 OHLCV 데이터 생성"""
    dates = pd.bdate_range(start, end)
    np.random.seed(42)
    n = len(dates)
    base_price = 70000.0
    returns = np.random.normal(0, 0.02, n)
    prices = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.uniform(-0.01, 0.01, n)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.015, n))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.015, n))),
            "close": prices,
            "volume": np.random.randint(500000, 2000000, n),
        },
        index=dates,
    )
    return df


@app.command()
def run(
    strategy: str = typer.Option(..., "--strategy", "-s", help="전략 이름 (예: MeanReversion)"),
    symbol: Optional[str] = typer.Option(None, "--symbol", help="종목 코드 (예: 005930)"),
    symbols: Optional[str] = typer.Option(None, "--symbols", help="쉼표 구분 종목 목록 (예: 005930,000660,373220)"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="종목 프리셋 (예: kospi10, mag7)"),
    market: str = typer.Option("KR", "--market", "-m", help="시장 (KR/US)"),
    start: str = typer.Option(..., "--start", help="시작일 (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="종료일 (YYYY-MM-DD)"),
    capital: float = typer.Option(10_000_000, "--capital", "-c", help="초기 자본금"),
    timeframe: str = typer.Option("1d", "--timeframe", "-t", help="봉 단위 (1d/1h)"),
):
    """백테스팅 실행"""
    start_dt = _parse_date(start)
    end_dt = _parse_date(end)

    if start_dt >= end_dt:
        console.print(Panel("[red]시작일이 종료일보다 같거나 늦습니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    # --symbol, --symbols, --preset 상호 배타 검증
    opt_count = sum(1 for v in (symbol, symbols, preset) if v is not None)
    if opt_count == 0:
        console.print(
            Panel("[red]--symbol, --symbols, --preset 중 하나를 지정해야 합니다.[/red]", title="오류")
        )
        raise typer.Exit(code=1)
    if opt_count > 1:
        console.print(
            Panel("[red]--symbol, --symbols, --preset은 동시에 사용할 수 없습니다.[/red]", title="오류")
        )
        raise typer.Exit(code=1)

    # 종목 리스트 및 시장 결정
    if preset:
        if preset not in SYMBOL_PRESETS:
            available = ", ".join(SYMBOL_PRESETS.keys())
            console.print(
                Panel(f"[red]프리셋 '{preset}'을 찾을 수 없습니다.\n사용 가능: {available}[/red]", title="오류")
            )
            raise typer.Exit(code=1)
        preset_cfg = SYMBOL_PRESETS[preset]
        symbol_list: List[str] = preset_cfg["symbols"]
        market_upper = preset_cfg["market"]
    elif symbols:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            console.print(Panel("[red]유효한 종목 코드가 없습니다.[/red]", title="오류"))
            raise typer.Exit(code=1)
        market_upper = market.upper()
    else:
        symbol_list = [symbol]
        market_upper = market.upper()

    if strategy not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        console.print(
            Panel(f"[red]전략 '{strategy}'을 찾을 수 없습니다.\n사용 가능: {available}[/red]", title="오류")
        )
        raise typer.Exit(code=1)

    if market_upper not in ("KR", "US"):
        console.print(Panel("[red]시장은 KR 또는 US만 지원합니다.[/red]", title="오류"))
        raise typer.Exit(code=1)

    tf = TimeframeType.D1 if timeframe == "1d" else TimeframeType.H1

    symbols_display = ", ".join(symbol_list)
    console.print(f"\n[bold cyan]백테스팅 시작[/bold cyan]")
    console.print(f"  전략: {strategy}")
    console.print(f"  종목: {symbols_display} ({market_upper}) [{len(symbol_list)}개]")
    if preset:
        console.print(f"  프리셋: {preset}")
    console.print(f"  기간: {start} ~ {end}")
    console.print(f"  자본금: {capital:,.0f}")
    console.print(f"  봉: {timeframe}\n")

    try:
        market_type = MarketType.KR if market_upper == "KR" else MarketType.US

        # DB 캐시에서 데이터 조회 (없으면 KIS API 호출)
        db = SessionLocal()
        provider = KISDataProvider()
        cached = CachedDataProvider(provider, db)

        data = {}
        with console.status("[bold green]데이터 수집 중..."):
            for sym in symbol_list:
                df = asyncio.get_event_loop().run_until_complete(
                    cached.fetch_ohlcv(sym, market_type, tf, start_dt, end_dt)
                )
                if not df.empty:
                    if "timestamp" in df.columns:
                        df = df.set_index("timestamp")
                    data[sym] = df
                    console.log(f"  {sym}: {len(df)}건 로드")
                else:
                    console.log(f"  [yellow]{sym}: 데이터 없음 (건너뜀)[/yellow]")
            asyncio.get_event_loop().run_until_complete(provider.close())
            db.close()

        if not data:
            console.print(Panel("[red]데이터를 수집할 수 없습니다.[/red]", title="오류"))
            raise typer.Exit(code=1)

        console.print(f"  데이터: {len(data)}개 종목 로드 완료\n")

        # 엔진 구성
        strategy_instance = get_strategy(strategy)
        broker = Broker(market=market_upper, timeframe=tf)

        with console.status("[bold green]백테스팅 실행 중..."):
            engine = BacktestEngine(
                strategy=strategy_instance,
                data=data,
                broker=broker,
                initial_capital=capital,
            )
            result = engine.run()

        _print_result(result, capital)

    except BacktestError as e:
        console.print(Panel(f"[red]{e.message}[/red]", title=f"오류 [{e.error_code}]"))
        raise typer.Exit(code=1)


def _print_result(result: dict, initial_capital: float) -> None:
    """백테스팅 결과를 Rich Table로 출력"""
    equity_curve = result["equity_curve"]
    trades = result["trades"]
    final_equity = result["final_equity"]

    # 성과 지표 계산
    if not equity_curve.empty and "equity" in equity_curve.columns:
        eq = equity_curve["equity"]
        total_ret = PerformanceMetrics.total_return(eq)
        annual_ret = PerformanceMetrics.annual_return(eq)
        sharpe = PerformanceMetrics.sharpe_ratio(eq)
        sortino = PerformanceMetrics.sortino_ratio(eq)
        mdd = PerformanceMetrics.max_drawdown(eq)
    else:
        total_ret = annual_ret = sharpe = sortino = mdd = 0.0

    # 거래 통계
    if trades:
        trades_df = _trades_to_df(trades)
        wr = PerformanceMetrics.win_rate(trades_df)
        pf = PerformanceMetrics.profit_factor(trades_df)
        max_wins = PerformanceMetrics.max_consecutive(trades_df, win=True)
        max_losses = PerformanceMetrics.max_consecutive(trades_df, win=False)
    else:
        wr = pf = 0.0
        max_wins = max_losses = 0

    # 성과 요약 테이블
    table = Table(title="백테스팅 결과", show_header=True, header_style="bold magenta")
    table.add_column("지표", style="cyan", width=25)
    table.add_column("값", justify="right", width=20)

    table.add_row("초기 자본금", f"{initial_capital:,.0f}")
    table.add_row("최종 자산", f"{final_equity:,.0f}")
    table.add_row("총 수익률", _color_pct(total_ret))
    table.add_row("연환산 수익률", _color_pct(annual_ret))
    table.add_row("샤프 비율", f"{sharpe:.4f}")
    table.add_row("소르티노 비율", f"{sortino:.4f}")
    table.add_row("최대 낙폭 (MDD)", f"[red]{mdd:.2%}[/red]")
    table.add_row("총 거래 수", str(len(trades)))
    table.add_row("승률", f"{wr:.2%}")
    table.add_row("수익 팩터", f"{pf:.4f}" if pf != float("inf") else "INF")
    table.add_row("최대 연승", str(max_wins))
    table.add_row("최대 연패", str(max_losses))

    console.print()
    console.print(table)

    # 최근 거래 요약
    if trades:
        _print_recent_trades(trades)


def _print_recent_trades(trades: list, limit: int = 10) -> None:
    """최근 거래 목록 출력"""
    table = Table(title=f"최근 거래 (최대 {limit}건)", show_header=True, header_style="bold yellow")
    table.add_column("날짜", width=12)
    table.add_column("종목", width=10)
    table.add_column("방향", width=6)
    table.add_column("수량", justify="right", width=8)
    table.add_column("체결가", justify="right", width=12)
    table.add_column("수수료", justify="right", width=10)

    for trade in trades[-limit:]:
        side_str = "[green]매수[/green]" if trade.side == OrderSide.BUY else "[red]매도[/red]"
        table.add_row(
            str(trade.fill_date.date()) if hasattr(trade.fill_date, "date") else str(trade.fill_date)[:10],
            trade.symbol,
            side_str,
            str(trade.quantity),
            f"{trade.fill_price:,.0f}",
            f"{trade.commission:,.0f}",
        )

    console.print()
    console.print(table)


def _trades_to_df(trades: list) -> pd.DataFrame:
    """FilledOrder 리스트를 거래 쌍(매수→매도) PnL DataFrame으로 변환"""
    paired = []
    buys = {}  # symbol -> list of buy trades

    for t in trades:
        if t.side == OrderSide.BUY:
            buys.setdefault(t.symbol, []).append(t)
        elif t.side == OrderSide.SELL and buys.get(t.symbol):
            buy = buys[t.symbol].pop(0)
            pnl = (t.fill_price - buy.fill_price) * t.quantity - buy.commission - t.commission
            paired.append({"pnl": pnl})

    return pd.DataFrame(paired) if paired else pd.DataFrame(columns=["pnl"])


def _color_pct(value: float) -> str:
    if value >= 0:
        return f"[green]{value:.2%}[/green]"
    return f"[red]{value:.2%}[/red]"


@app.command("list")
def list_backtests(
    limit: int = typer.Option(20, "--limit", "-n", help="조회 건수"),
):
    """최근 백테스팅 목록 조회"""
    try:
        from app.db.session import SessionLocal
        from app.db.models import Backtest

        db = SessionLocal()
        backtests = db.query(Backtest).order_by(Backtest.created_at.desc()).limit(limit).all()

        if not backtests:
            console.print("[yellow]저장된 백테스팅이 없습니다.[/yellow]")
            db.close()
            return

        table = Table(title="백테스팅 목록", show_header=True, header_style="bold magenta")
        table.add_column("ID", width=12)
        table.add_column("이름", width=20)
        table.add_column("전략", width=15)
        table.add_column("종목", width=10)
        table.add_column("수익률", justify="right", width=10)
        table.add_column("상태", width=10)
        table.add_column("생성일", width=12)

        for bt in backtests:
            ret_str = f"{float(bt.total_return):.2%}" if bt.total_return else "-"
            table.add_row(
                bt.id[:12],
                bt.name or "-",
                bt.strategy_name,
                ", ".join(bt.symbols) if bt.symbols else "-",
                ret_str,
                bt.job_status.value if bt.job_status else "-",
                str(bt.created_at.date()) if bt.created_at else "-",
            )

        console.print(table)
        db.close()

    except Exception as e:
        console.print(Panel(f"[red]DB 조회 실패: {e}[/red]", title="오류"))
        raise typer.Exit(code=1)


@app.command()
def show(
    backtest_id: str = typer.Argument(..., help="백테스팅 ID"),
):
    """백테스팅 상세 결과 조회"""
    try:
        from app.db.session import SessionLocal
        from app.db.models import Backtest

        db = SessionLocal()
        bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()

        if not bt:
            # 부분 ID 매칭
            bt = db.query(Backtest).filter(Backtest.id.like(f"{backtest_id}%")).first()

        if not bt:
            console.print(Panel(f"[red]백테스팅을 찾을 수 없습니다: {backtest_id}[/red]", title="오류"))
            db.close()
            raise typer.Exit(code=1)

        table = Table(title=f"백테스팅 상세: {bt.name or bt.id[:12]}", show_header=True, header_style="bold magenta")
        table.add_column("항목", style="cyan", width=25)
        table.add_column("값", justify="right", width=25)

        table.add_row("ID", bt.id)
        table.add_row("이름", bt.name or "-")
        table.add_row("전략", bt.strategy_name)
        table.add_row("시장", bt.market.value if bt.market else "-")
        table.add_row("종목", ", ".join(bt.symbols) if bt.symbols else "-")
        table.add_row("기간", f"{bt.start_date} ~ {bt.end_date}")
        table.add_row("초기 자본", f"{float(bt.initial_capital):,.0f}" if bt.initial_capital else "-")
        table.add_row("상태", bt.job_status.value if bt.job_status else "-")
        table.add_row("총 수익률", f"{float(bt.total_return):.2%}" if bt.total_return else "-")
        table.add_row("연환산 수익률", f"{float(bt.annual_return):.2%}" if bt.annual_return else "-")
        table.add_row("샤프 비율", f"{float(bt.sharpe_ratio):.4f}" if bt.sharpe_ratio else "-")
        table.add_row("소르티노 비율", f"{float(bt.sortino_ratio):.4f}" if bt.sortino_ratio else "-")
        table.add_row("최대 낙폭", f"{float(bt.max_drawdown):.2%}" if bt.max_drawdown else "-")
        table.add_row("승률", f"{float(bt.win_rate):.2%}" if bt.win_rate else "-")
        table.add_row("수익 팩터", f"{float(bt.profit_factor):.4f}" if bt.profit_factor else "-")
        table.add_row("총 거래 수", str(bt.total_trades) if bt.total_trades else "0")

        console.print(table)
        db.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(f"[red]DB 조회 실패: {e}[/red]", title="오류"))
        raise typer.Exit(code=1)
