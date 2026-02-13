import type { BacktestDetail } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { formatPercent, formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface MetricItem {
  label: string;
  value: string;
  color?: "green" | "red" | "default";
}

function getColor(val: number | null | undefined): "green" | "red" | "default" {
  if (val == null) return "default";
  return val >= 0 ? "green" : "red";
}

export function ResultsCard({ data }: { data: BacktestDetail }) {
  const metrics: MetricItem[] = [
    { label: "총 수익률", value: formatPercent(data.total_return), color: getColor(data.total_return) },
    { label: "연환산 수익률", value: formatPercent(data.annual_return), color: getColor(data.annual_return) },
    { label: "샤프 비율", value: formatNumber(data.sharpe_ratio), color: getColor(data.sharpe_ratio) },
    { label: "소르티노 비율", value: formatNumber(data.sortino_ratio), color: getColor(data.sortino_ratio) },
    { label: "MDD", value: formatPercent(data.max_drawdown), color: "red" },
    { label: "승률", value: formatPercent(data.win_rate), color: "default" },
    { label: "Profit Factor", value: formatNumber(data.profit_factor), color: getColor(data.profit_factor != null ? data.profit_factor - 1 : null) },
    { label: "총 거래 수", value: String(data.total_trades), color: "default" },
    { label: "최대 연속 승", value: String(data.max_consecutive_wins), color: "green" },
    { label: "최대 연속 패", value: String(data.max_consecutive_losses), color: "red" },
    { label: "평균 수익", value: formatPercent(data.avg_win), color: "green" },
    { label: "평균 손실", value: formatPercent(data.avg_loss), color: "red" },
  ];

  return (
    <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
      {metrics.map((m) => (
        <Card key={m.label}>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{m.label}</p>
            <p
              className={cn(
                "mt-1 text-lg font-semibold",
                m.color === "green" && "text-green-600",
                m.color === "red" && "text-red-600"
              )}
            >
              {m.value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
