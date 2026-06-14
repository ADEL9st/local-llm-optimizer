from __future__ import annotations

from statistics import mean
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    cleaned: list[float] = []
    for row in rows:
        value = to_float(row.get(key))
        if value is not None:
            cleaned.append(value)
    return cleaned


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, float] | None:
    numbers = metric_values(rows, key)
    if not numbers:
        return None

    return {
        "avg": round(mean(numbers), 2),
        "max": round(max(numbers), 2),
        "min": round(min(numbers), 2),
    }


def max_ratio(numerator_values: list[float], denominator_values: list[float]) -> float | None:
    if not numerator_values or not denominator_values:
        return None

    denominator = max(denominator_values)
    if denominator <= 0:
        return None

    return max(numerator_values) / denominator * 100
