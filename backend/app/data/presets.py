"""종목 프리셋 모듈."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SymbolPreset:
    name: str
    description: str
    market: str  # "KR" or "US"
    symbols: List[str] = field(default_factory=list)


PRESETS: Dict[str, SymbolPreset] = {
    "kospi10": SymbolPreset(
        name="kospi10",
        description="KOSPI 시가총액 상위 10종목",
        market="KR",
        symbols=[
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "373220",  # LG에너지솔루션
            "005380",  # 현대차
            "035420",  # NAVER
            "000270",  # 기아
            "068270",  # 셀트리온
            "035720",  # 카카오
            "051910",  # LG화학
            "006400",  # 삼성SDI
        ],
    ),
    "kospi20": SymbolPreset(
        name="kospi20",
        description="KOSPI 시가총액 상위 20종목",
        market="KR",
        symbols=[
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "373220",  # LG에너지솔루션
            "005380",  # 현대차
            "035420",  # NAVER
            "000270",  # 기아
            "068270",  # 셀트리온
            "035720",  # 카카오
            "051910",  # LG화학
            "006400",  # 삼성SDI
            "207940",  # 삼성바이오로직스
            "005490",  # POSCO홀딩스
            "055550",  # 신한지주
            "105560",  # KB금융
            "003670",  # 포스코퓨처엠
            "028260",  # 삼성물산
            "012330",  # 현대모비스
            "066570",  # LG전자
            "096770",  # SK이노베이션
            "003550",  # LG
        ],
    ),
    "mag7": SymbolPreset(
        name="mag7",
        description="미국 빅테크 Magnificent 7",
        market="US",
        symbols=[
            "AAPL",   # Apple
            "MSFT",   # Microsoft
            "GOOGL",  # Alphabet
            "AMZN",   # Amazon
            "NVDA",   # NVIDIA
            "META",   # Meta
            "TSLA",   # Tesla
        ],
    ),
}


def get_preset(name: str) -> SymbolPreset:
    """프리셋 이름으로 조회. case-insensitive."""
    key = name.lower()
    preset = PRESETS.get(key)
    if preset is None:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset: '{name}'. Available: {available}")
    return preset


def list_presets() -> List[SymbolPreset]:
    """등록된 모든 프리셋 목록 반환."""
    return list(PRESETS.values())
