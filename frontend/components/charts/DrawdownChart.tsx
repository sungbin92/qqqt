"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { EquityCurvePoint } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  data: EquityCurvePoint[];
}

export function DrawdownChart({ data }: Props) {
  if (!data || data.length === 0) return null;

  const ddData = data.map((d) => ({
    date: d.date,
    drawdown: d.drawdown != null ? d.drawdown * 100 : 0,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">낙폭 (Drawdown)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={ddData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
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
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                domain={["dataMin", 0]}
              />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(2)}%`, "Drawdown"]}
                labelFormatter={(label) => new Date(label).toLocaleDateString("ko-KR")}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#dc2626"
                fill="#fca5a5"
                fillOpacity={0.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
