"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import type { CompareBacktestResult } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5"];

interface Props {
  results: CompareBacktestResult[];
  initialCapital: number;
}

interface MergedPoint {
  date: string;
  [key: string]: number | string;
}

export function CompareEquityCurve({ results, initialCapital }: Props) {
  const validResults = results.filter(
    (r) => r.equity_curve_data && r.equity_curve_data.length > 0
  );
  if (validResults.length === 0) return null;

  // 모든 equity curve 데이터를 날짜 기준으로 병합
  const dateMap = new Map<string, MergedPoint>();

  for (const result of validResults) {
    for (const point of result.equity_curve_data!) {
      const raw = point as unknown as Record<string, unknown>;
      const date = (raw.timestamp as string) ?? (raw.date as string);
      if (!dateMap.has(date)) {
        dateMap.set(date, { date });
      }
      const entry = dateMap.get(date)!;
      entry[result.strategy_name] = raw.equity as number;
    }
  }

  const merged = Array.from(dateMap.values()).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">자산 곡선 비교 (Equity Curve Overlay)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={merged} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) =>
                  v >= 1_000_000
                    ? `${(v / 1_000_000).toFixed(1)}M`
                    : v >= 1_000
                    ? `${(v / 1_000).toFixed(0)}K`
                    : String(v)
                }
              />
              <Tooltip
                formatter={(value: number, name: string) => [
                  new Intl.NumberFormat("ko-KR").format(Math.round(value)),
                  name,
                ]}
                labelFormatter={(label) => new Date(label).toLocaleDateString("ko-KR")}
              />
              <Legend />
              <ReferenceLine
                y={initialCapital}
                stroke="#9ca3af"
                strokeDasharray="4 4"
                label={{ value: "초기자본", position: "right", fontSize: 11, fill: "#9ca3af" }}
              />
              {validResults.map((result, idx) => (
                <Line
                  key={result.strategy_name}
                  type="monotone"
                  dataKey={result.strategy_name}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
