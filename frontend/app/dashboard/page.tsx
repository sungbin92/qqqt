"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listBacktests } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { JobStatusBanner } from "@/components/JobStatusBanner";
import { formatPercent, formatDate } from "@/lib/utils";
import { Plus } from "lucide-react";

export default function DashboardPage() {
  const { data: backtests, isLoading, error } = useQuery({
    queryKey: ["backtests", 1, 5],
    queryFn: () => listBacktests(1, 5),
  });

  const runningJobs = backtests?.filter(
    (b) => b.job_status === "RUNNING" || b.job_status === "PENDING"
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            최근 백테스팅 현황을 확인하세요
          </p>
        </div>
        <Link href="/backtest/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            새 백테스팅
          </Button>
        </Link>
      </div>

      {/* 실행 중인 작업 */}
      {runningJobs && runningJobs.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">실행 중인 작업</h2>
          {runningJobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="p-4">
                <div className="mb-3 flex items-center justify-between">
                  <Link
                    href={`/backtest/${job.id}`}
                    className="font-medium hover:underline"
                  >
                    {job.name}
                  </Link>
                  <StatusBadge status={job.job_status} />
                </div>
                <JobStatusBanner
                  backtestId={job.id}
                  status={job.job_status}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 최근 백테스팅 */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">최근 백테스팅</h2>

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
              백테스팅 기록이 없습니다. 새 백테스팅을 시작해보세요.
            </CardContent>
          </Card>
        )}

        {backtests && backtests.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {backtests.map((bt) => (
              <Link key={bt.id} href={`/backtest/${bt.id}`}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{bt.name}</CardTitle>
                      <StatusBadge status={bt.job_status} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">전략</span>
                        <span className="font-medium">{bt.strategy_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">수익률</span>
                        <span
                          className={
                            bt.total_return != null
                              ? bt.total_return >= 0
                                ? "font-medium text-green-600"
                                : "font-medium text-red-600"
                              : "text-muted-foreground"
                          }
                        >
                          {formatPercent(bt.total_return)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">종목</span>
                        <span>{bt.symbols.join(", ")}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">생성일</span>
                        <span>{formatDate(bt.created_at)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
