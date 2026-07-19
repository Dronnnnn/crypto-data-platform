from dataclasses import dataclass


@dataclass(slots=True)
class Price:
    symbol: str
    price: float
    timestamp: str
