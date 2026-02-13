import type { JobStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusConfig: Record<JobStatus, { label: string; className: string }> = {
  PENDING: { label: "대기", className: "bg-gray-100 text-gray-700 border-gray-200" },
  RUNNING: { label: "실행중", className: "bg-blue-100 text-blue-700 border-blue-200" },
  COMPLETED: { label: "완료", className: "bg-green-100 text-green-700 border-green-200" },
  FAILED: { label: "실패", className: "bg-red-100 text-red-700 border-red-200" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const config = statusConfig[status];
  return (
    <Badge variant="outline" className={cn(config.className)}>
      {config.label}
    </Badge>
  );
}
