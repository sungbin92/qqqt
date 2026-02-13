"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { createBacktest } from "@/lib/api-client";
import type { BacktestCreate, MarketType, TimeframeType } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StrategySelector } from "@/components/StrategySelector";
import { getDefaultParams } from "@/lib/strategy-params";

interface FormErrors {
  name?: string;
  strategy?: string;
  symbols?: string;
  dates?: string;
  capital?: string;
}

export function BacktestForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL 파라미터에서 프리필 값 추출 (템플릿에서 넘어온 경우)
  const prefillStrategy = searchParams.get("strategy") ?? "";
  const prefillParams = (() => {
    const raw = searchParams.get("params");
    if (!raw) return prefillStrategy ? getDefaultParams(prefillStrategy) : {};
    try {
      return JSON.parse(raw) as Record<string, number>;
    } catch {
      return getDefaultParams(prefillStrategy);
    }
  })();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState(prefillStrategy);
  const [parameters, setParameters] = useState<Record<string, number>>(prefillParams);
  const [market, setMarket] = useState<MarketType>("KR");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [timeframe, setTimeframe] = useState<TimeframeType>("1d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState(10_000_000);
  const [errors, setErrors] = useState<FormErrors>({});

  const mutation = useMutation({
    mutationFn: createBacktest,
    onSuccess: (data) => {
      router.push(`/backtest/${data.job_id}`);
    },
  });

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) newErrors.name = "이름을 입력하세요";
    if (!strategy) newErrors.strategy = "전략을 선택하세요";

    const symbols = symbolsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (symbols.length === 0) newErrors.symbols = "종목을 1개 이상 입력하세요";

    if (!startDate || !endDate) {
      newErrors.dates = "시작일과 종료일을 입력하세요";
    } else if (startDate >= endDate) {
      newErrors.dates = "시작일은 종료일보다 이전이어야 합니다";
    }

    if (initialCapital <= 0) newErrors.capital = "초기 자본금은 0보다 커야 합니다";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const symbols = symbolsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const data: BacktestCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      strategy_name: strategy,
      parameters,
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

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 기본 정보 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">기본 정보</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">이름 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 삼성전자 평균회귀 테스트"
              className={inputClass}
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-500">{errors.name}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">설명</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="백테스팅 설명 (선택)"
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
        </CardContent>
      </Card>

      {/* 전략 선택 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">전략 설정</CardTitle>
        </CardHeader>
        <CardContent>
          <StrategySelector
            strategy={strategy}
            parameters={parameters}
            onStrategyChange={(name, params) => {
              setStrategy(name);
              setParameters(params);
            }}
            onParamChange={(key, value) => {
              setParameters((prev) => ({ ...prev, [key]: value }));
            }}
          />
          {errors.strategy && (
            <p className="mt-2 text-sm text-red-500">{errors.strategy}</p>
          )}
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
                <label key={m} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="market"
                    value={m}
                    checked={market === m}
                    onChange={() => setMarket(m)}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{m === "KR" ? "한국 (KR)" : "미국 (US)"}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">종목 코드 *</label>
            <input
              type="text"
              value={symbolsInput}
              onChange={(e) => setSymbolsInput(e.target.value)}
              placeholder={market === "KR" ? "예: 005930, 000660" : "예: AAPL, MSFT"}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              여러 종목은 콤마(,)로 구분하세요
            </p>
            {errors.symbols && (
              <p className="mt-1 text-sm text-red-500">{errors.symbols}</p>
            )}
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
            <label className="block text-sm font-medium mb-1.5">타임프레임 *</label>
            <div className="flex gap-4">
              {(["1d", "1h"] as const).map((tf) => (
                <label key={tf} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="timeframe"
                    value={tf}
                    checked={timeframe === tf}
                    onChange={() => setTimeframe(tf)}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{tf === "1d" ? "일봉 (1d)" : "시간봉 (1h)"}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium mb-1.5">시작일 *</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">종료일 *</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className={inputClass}
              />
            </div>
          </div>
          {errors.dates && (
            <p className="text-sm text-red-500">{errors.dates}</p>
          )}
          <div>
            <label className="block text-sm font-medium mb-1.5">초기 자본금 *</label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              min={1}
              className={inputClass}
            />
            {errors.capital && (
              <p className="mt-1 text-sm text-red-500">{errors.capital}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 제출 */}
      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.back()}
        >
          취소
        </Button>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "생성 중..." : "백테스팅 실행"}
        </Button>
      </div>

      {mutation.error && (
        <p className="text-sm text-red-500">
          오류: {(mutation.error as Error).message}
        </p>
      )}
    </form>
  );
}
