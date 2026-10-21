"""Plain-value workflow for backend chart indicator requests."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.indicator_catalog import compute_chart_indicators, list_chart_indicators

_MAX_BARS = 5000
_BAR_COLUMNS = ("time", "open", "high", "low", "close", "volume")


def coerce_bars(raw_bars: Any) -> pd.DataFrame:
    """Validate and normalize frontend OHLCV rows without Flask context."""
    if not isinstance(raw_bars, list):
        raise ValueError("bars must be a list")
    if not raw_bars:
        raise ValueError("bars cannot be empty")
    if len(raw_bars) > _MAX_BARS:
        raise ValueError(f"bars cannot exceed {_MAX_BARS}")

    rows = []
    for index, item in enumerate(raw_bars):
        if not isinstance(item, dict):
            raise ValueError(f"bars[{index}] must be an object")
        row = {}
        for key in _BAR_COLUMNS:
            raw_value = item.get(key)
            if raw_value is None and key == "time":
                raw_value = item.get("timestamp")
            if raw_value is None and key == "volume":
                raw_value = 0
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"bars[{index}].{key} is invalid") from exc
            if not value == value or value in (float("inf"), float("-inf")):
                raise ValueError(f"bars[{index}].{key} is invalid")
            row[key] = value
        rows.append(row)
    return pd.DataFrame(rows, columns=_BAR_COLUMNS)


def catalog() -> list[dict[str, Any]]:
    return list_chart_indicators()


def compute(raw_bars: Any, indicators: Any) -> list[dict[str, Any]]:
    bars = coerce_bars(raw_bars)
    if not isinstance(indicators, list):
        raise ValueError("indicators must be a list")
    if len(indicators) > 50:
        raise ValueError("too many indicators")
    return compute_chart_indicators(bars, indicators)
