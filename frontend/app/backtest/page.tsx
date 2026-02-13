"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listBacktests, deleteBacktest } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { formatPercent, formatNumber, formatDate } from "@/lib/utils";
import { Plus, Trash2, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 20;

export default function BacktestListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data: backtests, isLoading, error } = useQuery({
    queryKey: ["backtests", page, PAGE_SIZE],
    queryFn: () => listBacktests(page, PAGE_SIZE),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBacktest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
      setDeleteTarget(null);
    },
  });

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeleteTarget(id);
  };

  const confirmDelete = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">백테스팅 목록</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            백테스팅 실행 결과를 확인하세요
          </p>
        </div>
        <Link href="/backtest/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            새 백테스팅
          </Button>
        </Link>
      </div>

      {isLoading && (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            로딩 중...
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="p-6 text-center text-red-500">
            데이터를 불러오지 못했습니다: {(error as Error).message}
          </CardContent>
        </Card>
      )}

      {backtests && backtests.length === 0 && (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            백테스팅 기록이 없습니다.
          </CardContent>
        </Card>
      )}

      {backtests && backtests.length > 0 && (
        <div className="rounded-lg border">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left font-medium">이름</th>
                  <th className="px-4 py-3 text-left font-medium">전략</th>
                  <th className="px-4 py-3 text-left font-medium">시장</th>
                  <th className="px-4 py-3 text-right font-medium">수익률</th>
                  <th className="px-4 py-3 text-right font-medium">샤프</th>
                  <th className="px-4 py-3 text-right font-medium">MDD</th>
                  <th className="px-4 py-3 text-center font-medium">상태</th>
                  <th className="px-4 py-3 text-left font-medium">생성일</th>
                  <th className="px-4 py-3 text-center font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {backtests.map((bt) => (
                  <tr
                    key={bt.id}
                    className="border-b cursor-pointer transition-colors hover:bg-muted/50"
                    onClick={() => router.push(`/backtest/${bt.id}`)}
                  >
                    <td className="px-4 py-3 font-medium">{bt.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {bt.strategy_name}
                    </td>
                    <td className="px-4 py-3">{bt.market}</td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={
                          bt.total_return != null
                            ? bt.total_return >= 0
                              ? "text-green-600"
                              : "text-red-600"
                            : "text-muted-foreground"
                        }
                      >
                        {formatPercent(bt.total_return)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatNumber(bt.sharpe_ratio)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={bt.max_drawdown != null ? "text-red-600" : ""}>
                        {formatPercent(bt.max_drawdown)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <StatusBadge status={bt.job_status} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDate(bt.created_at)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-red-600"
                        onClick={(e) => handleDelete(e, bt.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 페이지네이션 */}
          <div className="flex items-center justify-between border-t px-4 py-3">
            <span className="text-sm text-muted-foreground">
              페이지 {page}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                이전
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={backtests.length < PAGE_SIZE}
                onClick={() => setPage((p) => p + 1)}
              >
                다음
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 삭제 확인 다이얼로그 */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-sm rounded-lg bg-background p-6 shadow-lg">
            <h3 className="text-lg font-semibold">백테스팅 삭제</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              이 백테스팅을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
                disabled={deleteMutation.isPending}
              >
                취소
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "삭제 중..." : "삭제"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
