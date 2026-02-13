import type {
  ApiResponse,
  BacktestCreate,
  BacktestDetail,
  BacktestSummary,
  CompareCreate,
  CompareResponse,
  JobResponse,
  JobStatusResponse,
  OptimizationDetail,
  OptimizeCreate,
  StrategyInfo,
  StrategyTemplate,
  StrategyTemplateCreate,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string | undefined,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  const json: ApiResponse<T> = await res.json();

  if (!res.ok || !json.success) {
    throw new ApiError(
      res.status,
      json.error_code ?? undefined,
      json.error || `API error: ${res.status}`
    );
  }

  return json.data as T;
}

// ── Backtest API ──

export async function createBacktest(data: BacktestCreate): Promise<JobResponse> {
  return request<JobResponse>("/api/backtest", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listBacktests(
  page = 1,
  limit = 20
): Promise<BacktestSummary[]> {
  return request<BacktestSummary[]>(
    `/api/backtest?page=${page}&limit=${limit}`
  );
}

export async function getBacktest(id: string): Promise<BacktestDetail> {
  const raw = await request<any>(`/api/backtest/${id}`);

  // API의 equity_curve_data ({timestamp, equity, cash}) → 프론트 타입 ({date, equity, drawdown})
  if (raw.equity_curve_data && raw.equity_curve_data.length > 0) {
    let peak = Number(raw.equity_curve_data[0].equity);
    raw.equity_curve_data = raw.equity_curve_data.map((p: any) => {
      const equity = Number(p.equity);
      if (equity > peak) peak = equity;
      const drawdown = peak > 0 ? (equity - peak) / peak : 0;
      return { date: p.timestamp, equity, drawdown };
    });
  }

  return raw as BacktestDetail;
}

export async function getBacktestStatus(id: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/backtest/${id}/status`);
}

export async function deleteBacktest(id: string): Promise<void> {
  return request<void>(`/api/backtest/${id}`, { method: "DELETE" });
}

// ── Strategy API ──

export async function listStrategies(): Promise<StrategyInfo[]> {
  return request<StrategyInfo[]>("/api/strategies");
}

export async function listStrategyTemplates(): Promise<StrategyTemplate[]> {
  return request<StrategyTemplate[]>("/api/strategies/templates");
}

export async function createStrategyTemplate(
  data: StrategyTemplateCreate
): Promise<StrategyTemplate> {
  return request<StrategyTemplate>("/api/strategies/templates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Optimization API ──

export async function createOptimization(data: OptimizeCreate): Promise<JobResponse> {
  return request<JobResponse>("/api/optimize", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getOptimization(id: string): Promise<OptimizationDetail> {
  return request<OptimizationDetail>(`/api/optimize/${id}`);
}

export async function getOptimizationStatus(id: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/optimize/${id}/status`);
}

// ── Compare API ──

export async function createComparison(data: CompareCreate): Promise<JobResponse> {
  return request<JobResponse>("/api/backtest/compare", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getComparison(id: string): Promise<CompareResponse> {
  return request<CompareResponse>(`/api/backtest/compare/${id}`);
}

export async function getComparisonStatus(id: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/backtest/compare/${id}/status`);
}

// ── Export ──

export function getExportUrl(backtestId: string): string {
  return `${API_BASE}/api/backtest/${backtestId}/export`;
}

export { ApiError };
