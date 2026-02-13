"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  createOptimization,
  getOptimization,
  getOptimizationStatus,
  listStrategies,
} from "@/lib/api-client";
import type {
  MarketType,
  TimeframeType,
  OptimizeCreate,
  OptimizationDetail,
  JobStatus,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { STRATEGY_PARAMS, type ParamDef } from "@/lib/strategy-params";
import { cn } from "@/lib/utils";

type ParamRange = { min: number; max: number; step: number };

export default function OptimizePage() {
  const [strategy, setStrategy] = useState("");
  const [ranges, setRanges] = useState<Record<string, ParamRange>>({});
  const [market, setMarket] = useState<MarketType>("KR");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [timeframe, setTimeframe] = useState<TimeframeType>("1d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState(10_000_000);
  const [metric, setMetric] = useState("sharpe_ratio");

  // 결과 상태
  const [optimizationId, setOptimizationId] = useState<string | null>(null);

  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: listStrategies,
  });

  const paramDefs: ParamDef[] = STRATEGY_PARAMS[strategy] ?? [];

  // 조합 수 계산
  const combinationCount = useMemo(() => {
    if (!strategy || Object.keys(ranges).length === 0) return 0;
    let count = 1;
    for (const r of Object.values(ranges)) {
      if (r.step <= 0) return 0;
      const n = Math.floor((r.max - r.min) / r.step) + 1;
      count *= Math.max(n, 1);
    }
    return count;
  }, [ranges, strategy]);

  const isTooMany = combinationCount > 10_000;

  // 전략 변경 시 ranges 초기화
  const handleStrategyChange = (name: string) => {
    setStrategy(name);
    const defs = STRATEGY_PARAMS[name] ?? [];
    const newRanges: Record<string, ParamRange> = {};
    for (const d of defs) {
      newRanges[d.key] = {
        min: d.min ?? d.default,
        max: d.max ?? d.default,
        step: d.step ?? 1,
      };
    }
    setRanges(newRanges);
    setOptimizationId(null);
  };

  const updateRange = (key: string, field: keyof ParamRange, value: number) => {
    setRanges((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  };

  const mutation = useMutation({
    mutationFn: createOptimization,
    onSuccess: (data) => {
      setOptimizationId(data.job_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!strategy || isTooMany) return;

    const symbols = symbolsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const data: OptimizeCreate = {
      strategy_name: strategy,
      parameter_ranges: ranges,
      market,
      symbols,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      optimization_metric: metric,
    };

    mutation.mutate(data);
  };

  const inputClass =
    "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">파라미터 최적화</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Grid Search로 최적 파라미터 조합을 찾으세요
        </p>
      </div>

      {!optimizationId ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 전략 선택 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">전략 선택</CardTitle>
            </CardHeader>
            <CardContent>
              {strategiesLoading ? (
                <div className="h-10 rounded-md border bg-muted animate-pulse" />
              ) : (
                <select
                  value={strategy}
                  onChange={(e) => handleStrategyChange(e.target.value)}
                  className={inputClass}
                >
                  <option value="">전략을 선택하세요</option>
                  {strategies?.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
            </CardContent>
          </Card>

          {/* 파라미터 범위 설정 */}
          {strategy && paramDefs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">파라미터 범위</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {paramDefs.map((def) => {
                  const r = ranges[def.key];
                  if (!r) return null;
                  return (
                    <div key={def.key} className="rounded-lg border p-3">
                      <label className="block text-sm font-medium mb-2">
                        {def.label}
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">
                            Min
                          </label>
                          <input
                            type="number"
                            value={r.min}
                            step={def.step ?? (def.type === "int" ? 1 : 0.01)}
                            onChange={(e) =>
                              updateRange(def.key, "min", Number(e.target.value))
                            }
                            className={inputClass}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">
                            Max
                          </label>
                          <input
                            type="number"
                            value={r.max}
                            step={def.step ?? (def.type === "int" ? 1 : 0.01)}
                            onChange={(e) =>
                              updateRange(def.key, "max", Number(e.target.value))
                            }
                            className={inputClass}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">
                            Step
                          </label>
                          <input
                            type="number"
                            value={r.step}
                            step={def.step ?? (def.type === "int" ? 1 : 0.01)}
                            min={0.001}
                            onChange={(e) =>
                              updateRange(def.key, "step", Number(e.target.value))
                            }
                            className={inputClass}
                          />
                        </div>
                      </div>
                      {def.description && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {def.description}
                        </p>
                      )}
                    </div>
                  );
                })}

                {/* 조합 수 표시 */}
                <div
                  className={cn(
                    "rounded-lg border p-3 text-center",
                    isTooMany
                      ? "border-red-300 bg-red-50"
                      : "border-blue-300 bg-blue-50"
                  )}
                >
                  <span
                    className={cn(
                      "text-sm font-medium",
                      isTooMany ? "text-red-700" : "text-blue-700"
                    )}
                  >
                    총 조합 수: {combinationCount.toLocaleString()}개
                  </span>
                  {isTooMany && (
                    <p className="mt-1 text-xs text-red-600">
                      최대 10,000개까지 허용됩니다. 범위를 줄이거나 step을
                      늘려주세요.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 시장 & 종목 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">시장 & 종목</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  시장 *
                </label>
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
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  최적화 기준 지표
                </label>
                <select
                  value={metric}
                  onChange={(e) => setMetric(e.target.value)}
                  className={inputClass}
                >
                  <option value="sharpe_ratio">Sharpe Ratio</option>
                  <option value="sortino_ratio">Sortino Ratio</option>
                  <option value="total_return">Total Return</option>
                  <option value="annual_return">Annual Return</option>
                  <option value="max_drawdown">Max Drawdown (낮을수록 좋음)</option>
                </select>
              </div>
            </CardContent>
          </Card>

          {/* 제출 */}
          <div className="flex justify-end gap-3">
            <Button
              type="submit"
              disabled={
                mutation.isPending || !strategy || isTooMany || combinationCount === 0
              }
            >
              {mutation.isPending ? "생성 중..." : "최적화 실행"}
            </Button>
          </div>

          {mutation.error && (
            <p className="text-sm text-red-500">
              오류: {(mutation.error as Error).message}
            </p>
          )}
        </form>
      ) : (
        <OptimizationResult
          optimizationId={optimizationId}
          onReset={() => setOptimizationId(null)}
        />
      )}
    </div>
  );
}

// ── 결과 뷰 ──

function OptimizationResult({
  optimizationId,
  onReset,
}: {
  optimizationId: string;
  onReset: () => void;
}) {
  const { data: statusData } = useQuery({
    queryKey: ["optimization-status", optimizationId],
    queryFn: () => getOptimizationStatus(optimizationId),
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
    queryKey: ["optimization-detail", optimizationId],
    queryFn: () => getOptimization(optimizationId),
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
                {status === "PENDING" ? "대기 중..." : "최적화 실행 중..."}
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
              최적화 실패: {detail.job_error}
            </p>
          </CardContent>
        </Card>
      )}

      {/* 결과 테이블 */}
      {isComplete && detail?.top_results && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              상위 {detail.top_results.length}개 결과
              <Badge variant="outline" className="ml-2">
                {detail.total_combinations.toLocaleString()}개 조합 중
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 px-2 font-medium">#</th>
                    {detail.top_results[0] &&
                      Object.keys(detail.top_results[0].parameters).map(
                        (key) => (
                          <th key={key} className="py-2 px-2 font-medium">
                            {key}
                          </th>
                        )
                      )}
                    <th className="py-2 px-2 font-medium">수익률</th>
                    <th className="py-2 px-2 font-medium">연수익률</th>
                    <th className="py-2 px-2 font-medium">Sharpe</th>
                    <th className="py-2 px-2 font-medium">Sortino</th>
                    <th className="py-2 px-2 font-medium">MDD</th>
                    <th className="py-2 px-2 font-medium">거래 수</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.top_results.map((row, idx) => (
                    <tr key={idx} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-2">{idx + 1}</td>
                      {Object.values(row.parameters).map((val, i) => (
                        <td key={i} className="py-2 px-2">
                          {typeof val === "number" ? val.toFixed(4).replace(/\.?0+$/, "") : val}
                        </td>
                      ))}
                      <td className="py-2 px-2">
                        {row.total_return != null
                          ? `${(row.total_return * 100).toFixed(2)}%`
                          : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {row.annual_return != null
                          ? `${(row.annual_return * 100).toFixed(2)}%`
                          : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {row.sharpe_ratio != null
                          ? row.sharpe_ratio.toFixed(3)
                          : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {row.sortino_ratio != null
                          ? row.sortino_ratio.toFixed(3)
                          : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {row.max_drawdown != null
                          ? `${(row.max_drawdown * 100).toFixed(2)}%`
                          : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {row.total_trades ?? "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 돌아가기 */}
      <div className="flex justify-end">
        <Button variant="outline" onClick={onReset}>
          새 최적화 실행
        </Button>
      </div>
    </div>
  );
}
