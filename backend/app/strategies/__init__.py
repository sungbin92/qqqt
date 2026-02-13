from typing import Any, Dict, Type

from .base import Strategy
from .bollinger_bands import BollingerBandsStrategy
from .macd_crossover import MACDCrossoverStrategy
from .mean_reversion import MeanReversionStrategy
from .momentum_breakout import MomentumBreakoutStrategy
from .rsi import RSIStrategy

STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    "mean_reversion": MeanReversionStrategy,
    "momentum_breakout": MomentumBreakoutStrategy,
    "bollinger_bands": BollingerBandsStrategy,
    "rsi": RSIStrategy,
    "macd_crossover": MACDCrossoverStrategy,
}


def get_strategy(name: str, parameters: Dict[str, Any] = None) -> Strategy:
    """전략 이름으로 인스턴스를 생성하여 반환."""
    strategy_cls = STRATEGY_REGISTRY.get(name)
    if strategy_cls is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy: '{name}'. Available: {available}")
    return strategy_cls(parameters)
