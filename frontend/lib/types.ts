// ── Enums ──

export type MarketType = "KR" | "US";
export type TimeframeType = "1h" | "1d";
export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
export type OrderSide = "BUY" | "SELL";

// ── API Response ──

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  error_code?: string;
  meta?: Record<string, unknown>;
  timestamp: string;
}

export interface PaginationMeta {
  page: number;
  total: number;
  limit: number;
}

// ── Backtest ──

export interface BacktestCreate {
  name: string;
  description?: string;
  strategy_name: string;
  parameters: Record<string, unknown>;
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;
}

export interface BacktestSummary {
  id: string;
  name: string;
  strategy_name: string;
  market: MarketType;
  symbols: string[];
  job_status: JobStatus;
  total_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  total_trades: number;
  created_at: string;
}

export interface BacktestDetail {
  id: string;
  name: string;
  description: string | null;
  strategy_name: string;
  parameters: Record<string, unknown>;
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;

  job_status: JobStatus;
  job_error: string | null;
  progress: number;

  // 성과 지표
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  total_trades: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  avg_win: number | null;
  avg_loss: number | null;

  equity_curve_data: EquityCurvePoint[] | null;
  trades: TradeResponse[];
  created_at: string;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
  drawdown?: number;
}

// ── Trade ──

export interface TradeResponse {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  signal_price: number;
  signal_date: string;
  fill_price: number;
  fill_date: string;
  commission: number;
  exit_fill_price: number | null;
  exit_date: string | null;
  exit_commission: number | null;
  pnl: number | null;
  pnl_percent: number | null;
  holding_days: number | null;
}

// ── Job ──

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  status: JobStatus;
  progress: number;
}

// ── Strategy ──

export interface StrategyInfo {
  name: string;
  class: string;
}

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string | null;
  strategy_type: string;
  default_parameters: Record<string, unknown>;
  parameter_schema: Record<string, unknown> | null;
  created_at: string;
}

export interface StrategyTemplateCreate {
  name: string;
  description?: string;
  strategy_type: string;
  default_parameters: Record<string, unknown>;
  parameter_schema?: Record<string, unknown>;
}

// ── Optimization ──

export interface OptimizeCreate {
  strategy_name: string;
  parameter_ranges: Record<string, { min: number; max: number; step: number }>;
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;
  optimization_metric?: string;
}

export interface OptimizationDetail {
  id: string;
  strategy_name: string;
  parameter_ranges: Record<string, { min: number; max: number; step: number }>;
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;
  optimization_metric: string;
  total_combinations: number;

  job_status: JobStatus;
  job_error: string | null;
  progress: number;

  top_results: OptimizationResultItem[] | null;
  created_at: string;
}

// ── 전략 비교 ──

export interface StrategyCompareItem {
  strategy_name: string;
  parameters: Record<string, unknown>;
}

export interface CompareCreate {
  name: string;
  strategies: StrategyCompareItem[];
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;
}

export interface CompareBacktestResult {
  id: string;
  strategy_name: string;
  parameters: Record<string, unknown>;
  job_status: JobStatus;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  total_trades: number;
  equity_curve_data: EquityCurvePoint[] | null;
}

export interface CompareResponse {
  id: string;
  name: string;
  market: MarketType;
  symbols: string[];
  timeframe: TimeframeType;
  start_date: string;
  end_date: string;
  initial_capital: number;
  strategies: StrategyCompareItem[];
  job_status: JobStatus;
  job_error: string | null;
  progress: number;
  results: CompareBacktestResult[];
  created_at: string;
}

export interface OptimizationResultItem {
  parameters: Record<string, number>;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  total_trades: number | null;
  final_equity: number | null;
}
