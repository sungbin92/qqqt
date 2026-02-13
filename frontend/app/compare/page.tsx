"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  createComparison,
  getComparison,
  getComparisonStatus,
  listStrategies,
} from "@/lib/api-client";
import type {
  MarketType,
  TimeframeType,
  CompareCreate,
  CompareResponse,
  JobStatus,
  StrategyCompareItem,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { STRATEGY_PARAMS, getDefaultParams } from "@/lib/strategy-params";
import { cn, formatPercent, formatNumber } from "@/lib/utils";
import { CompareEquityCurve } from "@/components/charts/CompareEquityCurve";
import { RiskReturnScatter } from "@/components/charts/RiskReturnScatter";
import { Plus, Trash2 } from "lucide-react";

interface StrategyEntry {
  strategy_name: string;
  parameters: Record<string, number>;
}

export default function ComparePage() {
  const [name, setName] = useState("전략 비교");
  const [entries, setEntries] = useState<StrategyEntry[]>([
    { strategy_name: "", parameters: {} },
    { strategy_name: "", parameters: {} },
  ]);
  const [market, setMarket] = useState<MarketType>("KR");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [timeframe, setTimeframe] = useState<TimeframeType>("1d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState(10_000_000);

  const [comparisonId, setComparisonId] = useState<string | null>(null);

  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: listStrategies,
  });

  const updateEntry = (idx: number, field: string, value: unknown) => {
    setEntries((prev) => {
      const next = [...prev];
      if (field === "strategy_name") {
        const stratName = value as string;
        next[idx] = {
          strategy_name: stratName,
          parameters: getDefaultParams(stratName),
        };
      } else {
        next[idx] = { ...next[idx], [field]: value };
      }
      return next;
    });
  };

  const updateParam = (idx: number, key: string, value: number) => {
    setEntries((prev) => {
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        parameters: { ...next[idx].parameters, [key]: value },
      };
      return next;
    });
  };

  const addEntry = () => {
    if (entries.length >= 10) return;
    setEntries((prev) => [...prev, { strategy_name: "", parameters: {} }]);
  };

  const removeEntry = (idx: number) => {
    if (entries.length <= 2) return;
    setEntries((prev) => prev.filter((_, i) => i !== idx));
  };

  const mutation = useMutation({
    mutationFn: createComparison,
    onSuccess: (data) => {
      setComparisonId(data.job_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const symbols = symbolsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const strats: StrategyCompareItem[] = entries
      .filter((e) => e.strategy_name)
      .map((e) => ({
        strategy_name: e.strategy_name,
        parameters: e.parameters,
      }));

    if (strats.length < 2) return;

    const data: CompareCreate = {
      name,
      strategies: strats,
      market,
      symbols,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
    };

    mutation.mutate(data);
  };

  const inputClass =
    "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  const validCount = entries.filter((e) => e.strategy_name).length;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">전략 비교</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          동일 조건에서 여러 전략을 동시에 실행하고 성과를 비교하세요
        </p>
      </div>

      {!comparisonId ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 비교 이름 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">비교 설정</CardTitle>
            </CardHeader>
            <CardContent>
              <label className="block text-sm font-medium mb-1.5">비교 이름</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputClass}
                maxLength={200}
              />
            </CardContent>
          </Card>

          {/* 전략 목록 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">
                전략 선택
                <Badge variant="outline" className="ml-2">
                  {validCount}개
                </Badge>
              </CardTitle>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addEntry}
                disabled={entries.length >= 10}
              >
                <Plus className="h-4 w-4 mr-1" />
                추가
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {entries.map((entry, idx) => {
                const paramDefs = STRATEGY_PARAMS[entry.strategy_name] ?? [];
                return (
                  <div key={idx} className="rounded-lg border p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-muted-foreground min-w-[2rem]">
                        #{idx + 1}
                      </span>
                      {strategiesLoading ? (
                        <div className="h-10 flex-1 rounded-md border bg-muted animate-pulse" />
                      ) : (
                        <select
                          value={entry.strategy_name}
                          onChange={(e) =>
                            updateEntry(idx, "strategy_name", e.target.value)
                          }
                          className={cn(inputClass, "flex-1")}
                        >
                          <option value="">전략을 선택하세요</option>
                          {strategies?.map((s) => (
                            <option key={s.name} value={s.name}>
                              {s.name}
                            </option>
                          ))}
                        </select>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeEntry(idx)}
                        disabled={entries.length <= 2}
                        className="text-muted-foreground hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* 파라미터 */}
                    {entry.strategy_name && paramDefs.length > 0 && (
                      <div className="grid gap-3 sm:grid-cols-2 pl-8">
                        {paramDefs.map((def) => (
                          <div key={def.key}>
                            <label className="block text-xs text-muted-foreground mb-1">
                              {def.label}
                            </label>
                            <input
                              type="number"
                              value={entry.parameters[def.key] ?? def.default}
                              step={def.step ?? (def.type === "int" ? 1 : 0.01)}
                              min={def.min}
                              max={def.max}
                              onChange={(e) =>
                                updateParam(idx, def.key, Number(e.target.value))
                              }
                              className={cn(inputClass, "h-8 text-xs")}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* 시장 & 종목 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">시장 & 종목</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">시장 *</label>
                <div className="flex gap-4">
                  {(["KR", "US"] as const).map((m) => (
                    <label
                      key={m}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="market"
                        value={m}
                        checked={market === m}
                        onChange={() => setMarket(m)}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">
                        {m === "KR" ? "한국 (KR)" : "미국 (US)"}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  종목 코드 *
                </label>
                <input
                  type="text"
                  value={symbolsInput}
                  onChange={(e) => setSymbolsInput(e.target.value)}
                  placeholder={
                    market === "KR" ? "예: 005930, 000660" : "예: AAPL, MSFT"
                  }
                  className={inputClass}
                />
              </div>
            </CardContent>
          </Card>

          {/* 기간 & 설정 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">기간 & 설정</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  타임프레임 *
                </label>
                <div className="flex gap-4">
                  {(["1d", "1h"] as const).map((tf) => (
                    <label
                      key={tf}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="timeframe"
                        value={tf}
                        checked={timeframe === tf}
                        onChange={() => setTimeframe(tf)}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">
                        {tf === "1d" ? "일봉 (1d)" : "시간봉 (1h)"}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    시작일 *
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    종료일 *
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  초기 자본금 *
                </label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  min={1}
                  className={inputClass}
                />
              </div>
            </CardContent>
          </Card>

          {/* 제출 */}
          <div className="flex justify-end gap-3">
            <Button
              type="submit"
              disabled={mutation.isPending || validCount < 2}
            >
              {mutation.isPending ? "생성 중..." : `비교 실행 (${validCount}개 전략)`}
            </Button>
          </div>

          {mutation.error && (
            <p className="text-sm text-red-500">
              오류: {(mutation.error as Error).message}
            </p>
          )}
        </form>
      ) : (
        <ComparisonResult
          comparisonId={comparisonId}
          onReset={() => setComparisonId(null)}
        />
      )}
    </div>
  );
}

// ── 결과 뷰 ──

function ComparisonResult({
  comparisonId,
  onReset,
}: {
  comparisonId: string;
  onReset: () => void;
}) {
  const { data: statusData } = useQuery({
    queryKey: ["compare-status", comparisonId],
    queryFn: () => getComparisonStatus(comparisonId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "RUNNING" || status === "PENDING" ? 3000 : false;
    },
  });

  const status: JobStatus = statusData?.status ?? "PENDING";
  const progress = statusData?.progress ?? 0;
  const isComplete = status === "COMPLETED";
  const isFailed = status === "FAILED";

  const { data: detail } = useQuery({
    queryKey: ["compare-detail", comparisonId],
    queryFn: () => getComparison(comparisonId),
    enabled: isComplete || isFailed,
  });

  return (
    <div className="space-y-6">
      {/* 진행률 */}
      {!isComplete && !isFailed && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-700">
                {status === "PENDING"
                  ? "대기 중..."
                  : "전략 비교 실행 중..."}
              </span>
              <span className="text-sm text-blue-600">
                {Math.round(progress)}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-blue-200">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  status === "PENDING" ? "bg-gray-400" : "bg-blue-600"
                )}
                style={{
                  width: `${Math.max(progress, status === "PENDING" ? 0 : 2)}%`,
                }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* 에러 */}
      {isFailed && detail && (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <p className="text-sm text-red-600">
              비교 실패: {detail.job_error}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 결과 */}
      {isComplete && detail && (
        <>
          {/* 메타 정보 */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2">
                <h2 className="text-lg font-bold">{detail.name}</h2>
                <Badge variant="secondary">{detail.results.length}개 전략</Badge>
              </div>
              <div className="text-sm text-muted-foreground grid gap-1 sm:grid-cols-3">
                <span>시장: {detail.market}</span>
                <span>종목: {detail.symbols.join(", ")}</span>
                <span>기간: {new Date(detail.start_date).toLocaleDateString()} ~ {new Date(detail.end_date).toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>

          {/* 비교 테이블 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">성과 비교 테이블</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 px-2 font-medium">전략</th>
                      <th className="py-2 px-2 font-medium text-right">수익률</th>
                      <th className="py-2 px-2 font-medium text-right">연수익률</th>
                      <th className="py-2 px-2 font-medium text-right">Sharpe</th>
                      <th className="py-2 px-2 font-medium text-right">Sortino</th>
                      <th className="py-2 px-2 font-medium text-right">MDD</th>
                      <th className="py-2 px-2 font-medium text-right">승률</th>
                      <th className="py-2 px-2 font-medium text-right">Profit Factor</th>
                      <th className="py-2 px-2 font-medium text-right">거래 수</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.results.map((r) => (
                      <tr key={r.id} className="border-b hover:bg-muted/50">
                        <td className="py-2 px-2 font-medium">{r.strategy_name}</td>
                        <td
                          className={cn(
                            "py-2 px-2 text-right",
                            r.total_return != null && r.total_return > 0
                              ? "text-green-600"
                              : r.total_return != null && r.total_return < 0
                              ? "text-red-600"
                              : ""
                          )}
                        >
                          {formatPercent(r.total_return)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(r.annual_return)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatNumber(r.sharpe_ratio, 3)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatNumber(r.sortino_ratio, 3)}
                        </td>
                        <td className="py-2 px-2 text-right text-red-600">
                          {formatPercent(r.max_drawdown)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(r.win_rate)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatNumber(r.profit_factor, 2)}
                        </td>
                        <td className="py-2 px-2 text-right">{r.total_trades}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* 자산 곡선 오버레이 차트 */}
          <CompareEquityCurve
            results={detail.results}
            initialCapital={detail.initial_capital}
          />

          {/* 리스크/리턴 스캐터 플롯 */}
          <RiskReturnScatter results={detail.results} />
        </>
      )}

      {/* 돌아가기 */}
      <div className="flex justify-end">
        <Button variant="outline" onClick={onReset}>
          새 비교 실행
        </Button>
      </div>
    </div>
  );
}
