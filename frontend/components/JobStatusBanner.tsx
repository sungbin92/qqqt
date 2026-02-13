"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBacktestStatus } from "@/lib/api-client";
import type { JobStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface JobStatusBannerProps {
  backtestId: string;
  status: JobStatus;
  progress?: number;
  onComplete?: () => void;
}

export function JobStatusBanner({
  backtestId,
  status: initialStatus,
  progress: initialProgress = 0,
  onComplete,
}: JobStatusBannerProps) {
  const isRunning = initialStatus === "RUNNING" || initialStatus === "PENDING";

  const { data } = useQuery({
    queryKey: ["backtest-status", backtestId],
    queryFn: () => getBacktestStatus(backtestId),
    refetchInterval: isRunning ? 3000 : false,
    enabled: isRunning,
    initialData: { status: initialStatus, progress: initialProgress },
  });

  const status = data?.status ?? initialStatus;
  const progress = data?.progress ?? initialProgress;

  useEffect(() => {
    if (status === "COMPLETED" && onComplete) {
      onComplete();
    }
  }, [status, onComplete]);

  if (status !== "RUNNING" && status !== "PENDING") return null;

  return (
    <div className="rounded-lg border bg-blue-50 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-blue-700">
          {status === "PENDING" ? "대기 중..." : "실행 중..."}
        </span>
        <span className="text-sm text-blue-600">{Math.round(progress)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-blue-200">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            status === "PENDING" ? "bg-gray-400" : "bg-blue-600"
          )}
          style={{ width: `${Math.max(progress, status === "PENDING" ? 0 : 2)}%` }}
        />
      </div>
    </div>
  );
}
