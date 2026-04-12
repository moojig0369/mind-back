"""
EWMA тооцоолол — Exponentially Weighted Moving Average.
α = 0.3: сүүлийн утгад илүү жин өгнө.
"""

_ALPHA = 0.3


def calculate(levels: list[float]) -> float | None:
    """
    Хокинсын түвшний жагсаалтаас EWMA дундажийг тооцооно.
    Хамгийн хуучнаас шинэ рүү буцаана.
    """
    if not levels:
        return None
    ewma = float(levels[-1])
    for level in reversed(levels[:-1]):
        ewma = _ALPHA * level + (1 - _ALPHA) * ewma
    return ewma


def update(previous: float, current: float) -> float:
    """Нэг шинэ утгаар EWMA шинэчилнэ."""
    return round(_ALPHA * current + (1 - _ALPHA) * previous, 1)
