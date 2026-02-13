export interface ParamDef {
  key: string;
  label: string;
  type: "int" | "float";
  default: number;
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

export const STRATEGY_PARAMS: Record<string, ParamDef[]> = {
  mean_reversion: [
    { key: "lookback_period", label: "Lookback 기간", type: "int", default: 20, min: 5, max: 200, step: 1, description: "평균/표준편차 계산 기간" },
    { key: "entry_threshold", label: "진입 임계값", type: "float", default: 2.0, min: 0.5, max: 5.0, step: 0.1, description: "Z-Score 진입 기준" },
    { key: "exit_threshold", label: "청산 임계값", type: "float", default: 0.5, min: 0.0, max: 3.0, step: 0.1, description: "Z-Score 청산 기준" },
    { key: "position_weight", label: "포지션 비중", type: "float", default: 0.3, min: 0.01, max: 1.0, step: 0.01, description: "포트폴리오 투자 비중 (0~1)" },
  ],
  momentum_breakout: [
    { key: "ma_period", label: "이동평균 기간", type: "int", default: 20, min: 5, max: 200, step: 1, description: "이동평균 계산 기간" },
    { key: "volume_ma_period", label: "거래량 MA 기간", type: "int", default: 20, min: 5, max: 200, step: 1, description: "거래량 이동평균 기간" },
    { key: "volume_threshold", label: "거래량 배수", type: "float", default: 2.0, min: 1.0, max: 10.0, step: 0.1, description: "거래량 돌파 배수 기준" },
    { key: "stop_loss_pct", label: "손절 비율", type: "float", default: 0.05, min: 0.01, max: 0.5, step: 0.01, description: "손절 비율 (0.05 = 5%)" },
    { key: "take_profit_pct", label: "익절 비율", type: "float", default: 0.15, min: 0.01, max: 1.0, step: 0.01, description: "익절 비율 (0.15 = 15%)" },
    { key: "position_weight", label: "포지션 비중", type: "float", default: 0.3, min: 0.01, max: 1.0, step: 0.01, description: "포트폴리오 투자 비중 (0~1)" },
  ],
  bollinger_bands: [
    { key: "bb_period", label: "BB 기간", type: "int", default: 20, min: 5, max: 200, step: 1, description: "볼린저 밴드 계산 기간" },
    { key: "bb_std", label: "표준편차 배수", type: "float", default: 2.0, min: 0.5, max: 4.0, step: 0.1, description: "밴드 폭 (표준편차 배수)" },
    { key: "position_weight", label: "포지션 비중", type: "float", default: 0.3, min: 0.01, max: 1.0, step: 0.01, description: "포트폴리오 투자 비중 (0~1)" },
  ],
  rsi: [
    { key: "rsi_period", label: "RSI 기간", type: "int", default: 14, min: 2, max: 100, step: 1, description: "RSI 계산 기간" },
    { key: "oversold_threshold", label: "과매도 기준", type: "int", default: 30, min: 5, max: 50, step: 1, description: "매수 시그널 RSI 기준값" },
    { key: "overbought_threshold", label: "과매수 기준", type: "int", default: 70, min: 50, max: 95, step: 1, description: "매도 시그널 RSI 기준값" },
    { key: "position_weight", label: "포지션 비중", type: "float", default: 0.3, min: 0.01, max: 1.0, step: 0.01, description: "포트폴리오 투자 비중 (0~1)" },
  ],
  macd_crossover: [
    { key: "fast_period", label: "Fast EMA 기간", type: "int", default: 12, min: 2, max: 50, step: 1, description: "빠른 EMA 기간" },
    { key: "slow_period", label: "Slow EMA 기간", type: "int", default: 26, min: 10, max: 100, step: 1, description: "느린 EMA 기간" },
    { key: "signal_period", label: "시그널 기간", type: "int", default: 9, min: 2, max: 50, step: 1, description: "시그널 라인 기간" },
    { key: "position_weight", label: "포지션 비중", type: "float", default: 0.3, min: 0.01, max: 1.0, step: 0.01, description: "포트폴리오 투자 비중 (0~1)" },
  ],
};

export function getDefaultParams(strategyName: string): Record<string, number> {
  const defs = STRATEGY_PARAMS[strategyName];
  if (!defs) return {};
  return Object.fromEntries(defs.map((d) => [d.key, d.default]));
}
