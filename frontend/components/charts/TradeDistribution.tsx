"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import type { TradeResponse } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  trades: TradeResponse[];
}

function buildHistogram(trades: TradeResponse[]) {
  const pnls = trades
    .filter((t) => t.pnl_percent != null)
    .map((t) => t.pnl_percent! * 100);

  if (pnls.length === 0) return [];

  const min = Math.floor(Math.min(...pnls));
  const max = Math.ceil(Math.max(...pnls));
  const binSize = Math.max(1, Math.ceil((max - min) / 15));

  const bins: Record<number, number> = {};
  for (let b = min; b <= max; b += binSize) {
    bins[b] = 0;
  }

  for (const pnl of pnls) {
    const binKey = Math.floor((pnl - min) / binSize) * binSize + min;
    bins[binKey] = (bins[binKey] ?? 0) + 1;
  }

  return Object.entries(bins)
    .map(([k, v]) => ({ range: Number(k), count: v }))
    .sort((a, b) => a.range - b.range);
}

export function TradeDistribution({ trades }: Props) {
  const histogram = buildHistogram(trades);
  if (histogram.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">거래 PnL 분포</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogram} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="range"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                formatter={(value: number) => [value, "거래 수"]}
                labelFormatter={(label) => `${label}% ~ ${label + 1}%`}
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {histogram.map((entry) => (
                  <Cell
                    key={entry.range}
                    fill={entry.range >= 0 ? "#22c55e" : "#ef4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
