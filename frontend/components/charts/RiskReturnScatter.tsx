"use client";

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import type { CompareBacktestResult } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5"];

interface Props {
  results: CompareBacktestResult[];
}

export function RiskReturnScatter({ results }: Props) {
  const validResults = results.filter(
    (r) => r.max_drawdown != null && r.total_return != null
  );
  if (validResults.length === 0) return null;

  const data = validResults.map((r, idx) => ({
    name: r.strategy_name,
    risk: Math.abs(r.max_drawdown!) * 100,
    return: r.total_return! * 100,
    sharpe: r.sharpe_ratio,
    fill: COLORS[idx % COLORS.length],
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">리스크/리턴 (Risk-Return Scatter)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                type="number"
                dataKey="risk"
                name="MDD"
                tick={{ fontSize: 11 }}
                label={{ value: "MDD (%)", position: "bottom", fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="return"
                name="수익률"
                tick={{ fontSize: 11 }}
                label={{ value: "수익률 (%)", angle: -90, position: "insideLeft", fontSize: 12 }}
              />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || payload.length === 0) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border bg-background p-2 text-xs shadow-md">
                      <p className="font-semibold">{d.name}</p>
                      <p>수익률: {d.return.toFixed(2)}%</p>
                      <p>MDD: {d.risk.toFixed(2)}%</p>
                      {d.sharpe != null && <p>Sharpe: {d.sharpe.toFixed(3)}</p>}
                    </div>
                  );
                }}
              />
              <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
              <Scatter data={data} fill="#2563eb">
                {data.map((entry, idx) => (
                  <circle
                    key={idx}
                    cx={0}
                    cy={0}
                    r={8}
                    fill={entry.fill}
                    stroke={entry.fill}
                    strokeWidth={2}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        {/* 범례 */}
        <div className="mt-3 flex flex-wrap gap-3 justify-center">
          {data.map((d) => (
            <div key={d.name} className="flex items-center gap-1.5 text-xs">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: d.fill }}
              />
              {d.name}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
