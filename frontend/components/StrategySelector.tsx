"use client";

import { useQuery } from "@tanstack/react-query";
import { listStrategies } from "@/lib/api-client";
import { STRATEGY_PARAMS, getDefaultParams, type ParamDef } from "@/lib/strategy-params";

interface StrategySelectorProps {
  strategy: string;
  parameters: Record<string, number>;
  onStrategyChange: (name: string, params: Record<string, number>) => void;
  onParamChange: (key: string, value: number) => void;
}

export function StrategySelector({
  strategy,
  parameters,
  onStrategyChange,
  onParamChange,
}: StrategySelectorProps) {
  const { data: strategies, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: listStrategies,
  });

  const paramDefs: ParamDef[] = STRATEGY_PARAMS[strategy] ?? [];

  return (
    <div className="space-y-4">
      {/* 전략 선택 */}
      <div>
        <label className="block text-sm font-medium mb-1.5">전략 *</label>
        {isLoading ? (
          <div className="h-10 rounded-md border bg-muted animate-pulse" />
        ) : (
          <select
            value={strategy}
            onChange={(e) => {
              const name = e.target.value;
              onStrategyChange(name, getDefaultParams(name));
            }}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="">전략을 선택하세요</option>
            {strategies?.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* 전략 파라미터 */}
      {strategy && paramDefs.length > 0 && (
        <div className="rounded-lg border p-4 space-y-4">
          <h4 className="text-sm font-medium text-muted-foreground">전략 파라미터</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            {paramDefs.map((def) => (
              <div key={def.key}>
                <label className="block text-sm font-medium mb-1">
                  {def.label}
                </label>
                <input
                  type="number"
                  value={parameters[def.key] ?? def.default}
                  min={def.min}
                  max={def.max}
                  step={def.step ?? (def.type === "int" ? 1 : 0.01)}
                  onChange={(e) => {
                    const val = def.type === "int"
                      ? parseInt(e.target.value, 10)
                      : parseFloat(e.target.value);
                    if (!isNaN(val)) onParamChange(def.key, val);
                  }}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                {def.description && (
                  <p className="mt-1 text-xs text-muted-foreground">{def.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
