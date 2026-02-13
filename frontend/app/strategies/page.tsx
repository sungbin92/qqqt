"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listStrategies,
  listStrategyTemplates,
  createStrategyTemplate,
} from "@/lib/api-client";
import type { StrategyTemplateCreate } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { STRATEGY_PARAMS, getDefaultParams } from "@/lib/strategy-params";
import { formatDate } from "@/lib/utils";
import { FlaskConical, Plus, Play, X } from "lucide-react";

export default function StrategiesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: listStrategies,
  });

  const { data: templates = [] } = useQuery({
    queryKey: ["strategy-templates"],
    queryFn: listStrategyTemplates,
  });

  const handleUseTemplate = (template: {
    strategy_type: string;
    default_parameters: Record<string, unknown>;
  }) => {
    const params = new URLSearchParams();
    params.set("strategy", template.strategy_type);
    params.set("params", JSON.stringify(template.default_parameters));
    router.push(`/backtest/new?${params.toString()}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">전략 관리</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            사용 가능한 전략과 저장된 템플릿을 관리합니다
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />새 템플릿
        </Button>
      </div>

      {/* 사용 가능한 전략 */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">사용 가능한 전략</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {strategies.map((s) => {
            const paramDefs = STRATEGY_PARAMS[s.name];
            return (
              <Card key={s.name}>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FlaskConical className="h-4 w-4" />
                    {s.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    클래스: {s.class}
                  </p>
                  {paramDefs && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium">기본 파라미터:</p>
                      <div className="flex flex-wrap gap-1">
                        {paramDefs.map((p) => (
                          <Badge key={p.key} variant="outline" className="text-xs">
                            {p.label}: {p.default}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      const params = new URLSearchParams();
                      params.set("strategy", s.name);
                      router.push(`/backtest/new?${params.toString()}`);
                    }}
                  >
                    <Play className="mr-2 h-3 w-3" />이 전략으로 백테스팅
                  </Button>
                </CardContent>
              </Card>
            );
          })}
          {strategies.length === 0 && (
            <p className="text-sm text-muted-foreground col-span-2">
              등록된 전략이 없습니다.
            </p>
          )}
        </div>
      </div>

      {/* 저장된 템플릿 */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">저장된 템플릿</h2>
        {templates.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center text-muted-foreground">
              저장된 템플릿이 없습니다. 새 템플릿을 만들어보세요.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((t) => (
              <Card key={t.id}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{t.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {t.description && (
                    <p className="text-xs text-muted-foreground">
                      {t.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{t.strategy_type}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(t.created_at)}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(t.default_parameters).map(([k, v]) => (
                      <Badge key={k} variant="secondary" className="text-xs">
                        {k}: {String(v)}
                      </Badge>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleUseTemplate(t)}
                  >
                    <Play className="mr-2 h-3 w-3" />이 템플릿으로 백테스팅
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 새 템플릿 생성 다이얼로그 */}
      {showCreateDialog && (
        <CreateTemplateDialog
          strategies={strategies.map((s) => s.name)}
          onClose={() => setShowCreateDialog(false)}
          onCreated={() => {
            queryClient.invalidateQueries({ queryKey: ["strategy-templates"] });
            setShowCreateDialog(false);
          }}
        />
      )}
    </div>
  );
}

// ── 템플릿 생성 다이얼로그 ──

function CreateTemplateDialog({
  strategies,
  onClose,
  onCreated,
}: {
  strategies: string[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategyType, setStrategyType] = useState(strategies[0] ?? "");
  const [parameters, setParameters] = useState<Record<string, number>>(() =>
    getDefaultParams(strategies[0] ?? "")
  );

  const mutation = useMutation({
    mutationFn: createStrategyTemplate,
    onSuccess: () => onCreated(),
  });

  const handleStrategyChange = (newStrategy: string) => {
    setStrategyType(newStrategy);
    setParameters(getDefaultParams(newStrategy));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !strategyType) return;

    const data: StrategyTemplateCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      strategy_type: strategyType,
      default_parameters: parameters,
    };

    mutation.mutate(data);
  };

  const paramDefs = STRATEGY_PARAMS[strategyType] ?? [];

  const inputClass =
    "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg bg-background p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">새 템플릿 저장</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">템플릿 이름 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 보수적 평균회귀"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">설명</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="템플릿 설명 (선택)"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">전략 *</label>
            <select
              value={strategyType}
              onChange={(e) => handleStrategyChange(e.target.value)}
              className={inputClass}
            >
              {strategies.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {paramDefs.length > 0 && (
            <div className="space-y-3">
              <label className="block text-sm font-medium">파라미터</label>
              <div className="grid gap-3 sm:grid-cols-2">
                {paramDefs.map((p) => (
                  <div key={p.key}>
                    <label className="block text-xs text-muted-foreground mb-1">
                      {p.label}
                    </label>
                    <input
                      type="number"
                      value={parameters[p.key] ?? p.default}
                      onChange={(e) =>
                        setParameters((prev) => ({
                          ...prev,
                          [p.key]: Number(e.target.value),
                        }))
                      }
                      min={p.min}
                      max={p.max}
                      step={p.step}
                      className={inputClass}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={mutation.isPending || !name.trim()}>
              {mutation.isPending ? "저장 중..." : "저장"}
            </Button>
          </div>

          {mutation.error && (
            <p className="text-sm text-red-500">
              오류: {(mutation.error as Error).message}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
