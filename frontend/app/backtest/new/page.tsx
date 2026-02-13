"use client";

import { Suspense } from "react";
import { BacktestForm } from "@/components/BacktestForm";

export default function NewBacktestPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">새 백테스팅</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          전략과 파라미터를 설정하고 백테스팅을 실행하세요
        </p>
      </div>
      <Suspense fallback={<div className="text-muted-foreground">로딩 중...</div>}>
        <BacktestForm />
      </Suspense>
    </div>
  );
}
