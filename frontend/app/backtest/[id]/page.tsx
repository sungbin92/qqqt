"use client";

import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getBacktest, getExportUrl } from "@/lib/api-client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { JobStatusBanner } from "@/components/JobStatusBanner";
import { ResultsCard } from "@/components/ResultsCard";
import { TradesTable } from "@/components/TradesTable";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { TradeDistribution } from "@/components/charts/TradeDistribution";
import { formatDate } from "@/lib/utils";
import { Download, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function BacktestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["backtest", id],
    queryFn: () => getBacktest(id),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        로딩 중...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20 text-red-500">
        데이터를 불러오지 못했습니다: {(error as Error).message}
      </div>
    );
  }

  if (!data) return null;

  const isRunning = data.job_status === "RUNNING" || data.job_status === "PENDING";
  const isFailed = data.job_status === "FAILED";
  const isCompleted = data.job_status === "COMPLETED";

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link href="/backtest">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold">{data.name}</h1>
            <StatusBadge status={data.job_status} />
          </div>
          {data.description && (
            <p className="ml-11 text-sm text-muted-foreground">{data.description}</p>
          )}
        </div>
        {isCompleted && (
          <a href={getExportUrl(id)} download>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              CSV 다운로드
            </Button>
          </a>
        )}
      </div>

      {/* 메타 정보 */}
      <div className="ml-11 flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span>전략: <strong className="text-foreground">{data.strategy_name}</strong></span>
        <span>시장: <Badge variant="outline">{data.market}</Badge></span>
        <span>종목: {data.symbols.join(", ")}</span>
        <span>기간: {formatDate(data.start_date)} ~ {formatDate(data.end_date)}</span>
        <span>타임프레임: {data.timeframe}</span>
      </div>

      {/* PENDING / RUNNING */}
      {isRunning && (
        <JobStatusBanner
          backtestId={id}
          status={data.job_status}
          progress={data.progress}
          onComplete={() => {
            queryClient.invalidateQueries({ queryKey: ["backtest", id] });
          }}
        />
      )}

      {/* FAILED */}
      {isFailed && (
        <Card>
          <CardContent className="p-6">
            <p className="font-medium text-red-600">백테스팅 실패</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {data.job_error || "알 수 없는 오류가 발생했습니다."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* COMPLETED - 결과 */}
      {isCompleted && (
        <>
          {/* 성과 지표 카드 */}
          <ResultsCard data={data} />

          {/* 차트 */}
          {data.equity_curve_data && data.equity_curve_data.length > 0 && (
            <div className="space-y-4">
              <EquityCurveChart
                data={data.equity_curve_data}
                initialCapital={data.initial_capital}
              />
              <DrawdownChart data={data.equity_curve_data} />
            </div>
          )}

          {/* 거래 PnL 분포 */}
          {data.trades.length > 0 && (
            <TradeDistribution trades={data.trades} />
          )}

          {/* 거래 내역 테이블 */}
          <TradesTable trades={data.trades} />
        </>
      )}
    </div>
  );
}
