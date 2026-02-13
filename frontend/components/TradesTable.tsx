"use client";

import { useState, useMemo } from "react";
import type { TradeResponse } from "@/lib/types";
import { formatNumber, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";

interface Props {
  trades: TradeResponse[];
}

type SortKey = "fill_date" | "symbol" | "pnl" | "pnl_percent" | "holding_days";

const PAGE_SIZE = 15;

export function TradesTable({ trades }: Props) {
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>("fill_date");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    const arr = [...trades];
    arr.sort((a, b) => {
      let aVal: number | string = 0;
      let bVal: number | string = 0;

      switch (sortKey) {
        case "fill_date":
          aVal = a.fill_date;
          bVal = b.fill_date;
          break;
        case "symbol":
          aVal = a.symbol;
          bVal = b.symbol;
          break;
        case "pnl":
          aVal = a.pnl ?? 0;
          bVal = b.pnl ?? 0;
          break;
        case "pnl_percent":
          aVal = a.pnl_percent ?? 0;
          bVal = b.pnl_percent ?? 0;
          break;
        case "holding_days":
          aVal = a.holding_days ?? 0;
          bVal = b.holding_days ?? 0;
          break;
      }

      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });
    return arr;
  }, [trades, sortKey, sortAsc]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
    setPage(1);
  };

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      className="px-3 py-2.5 text-left font-medium cursor-pointer select-none hover:bg-muted/80"
      onClick={() => toggleSort(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
      </span>
    </th>
  );

  if (trades.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          거래 내역이 없습니다.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">거래 내역 ({trades.length}건)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <SortHeader label="종목" field="symbol" />
                <th className="px-3 py-2.5 text-left font-medium">방향</th>
                <th className="px-3 py-2.5 text-right font-medium">수량</th>
                <th className="px-3 py-2.5 text-right font-medium">시그널가</th>
                <th className="px-3 py-2.5 text-right font-medium">체결가</th>
                <th className="px-3 py-2.5 text-right font-medium">청산가</th>
                <SortHeader label="PnL" field="pnl" />
                <SortHeader label="PnL %" field="pnl_percent" />
                <SortHeader label="보유일" field="holding_days" />
                <SortHeader label="체결일" field="fill_date" />
              </tr>
            </thead>
            <tbody>
              {paged.map((t) => (
                <tr key={t.id} className="border-b hover:bg-muted/30">
                  <td className="px-3 py-2">{t.symbol}</td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "text-xs font-medium",
                        t.side === "BUY" ? "text-red-600" : "text-blue-600"
                      )}
                    >
                      {t.side === "BUY" ? "매수" : "매도"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">{t.quantity.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(t.signal_price, 0)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(t.fill_price, 0)}</td>
                  <td className="px-3 py-2 text-right">
                    {t.exit_fill_price != null ? formatNumber(t.exit_fill_price, 0) : "-"}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 text-right",
                      t.pnl != null && t.pnl >= 0 ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {t.pnl != null ? Math.round(t.pnl).toLocaleString() : "-"}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 text-right",
                      t.pnl_percent != null && t.pnl_percent >= 0
                        ? "text-green-600"
                        : "text-red-600"
                    )}
                  >
                    {t.pnl_percent != null ? `${(t.pnl_percent * 100).toFixed(2)}%` : "-"}
                  </td>
                  <td className="px-3 py-2 text-right">{t.holding_days ?? "-"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{formatDate(t.fill_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-3 pt-3 border-t">
            <span className="text-xs text-muted-foreground">
              {page}/{totalPages} 페이지
            </span>
            <div className="flex gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
