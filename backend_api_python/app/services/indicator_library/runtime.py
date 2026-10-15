"""Shared numerical helpers for the unified indicator library."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous = close.shift(1)
    tr = pd.concat([high - low, (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1)
    return _wilder(tr, period)


def _bar(key: str, title: str, values: Any, *, color: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": key,
        "title": title,
        "type": "bar",
        "data": _clean(values),
        "overlay": False,
        "baseValue": 0,
    }
    if color:
        item["color"] = color
    return item


def _clean(values: Any) -> list[Any]:
    result: list[Any] = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            result.append(None)
            continue
        result.append(numeric if np.isfinite(numeric) else None)
    return result


def _close(df: pd.DataFrame) -> pd.Series:
    return _series(df, "close")


def _ema(values: pd.Series, period: int) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    finite = pd.to_numeric(values, errors="coerce")
    valid_positions = np.flatnonzero(np.isfinite(finite.to_numpy(dtype=float, copy=False)))
    if len(valid_positions) < period:
        return result
    seed_end_pos = valid_positions[period - 1]
    seed_values = finite.iloc[valid_positions[:period]]
    seed = seed_values.mean()
    if not np.isfinite(seed):
        return result
    result.iloc[seed_end_pos] = seed
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_end_pos + 1, len(finite)):
        current = finite.iloc[index]
        previous = result.iloc[index - 1]
        result.iloc[index] = previous if not np.isfinite(current) else (current - previous) * alpha + previous
    return result


def _integer(params: Mapping[str, Any], key: str, default: int, minimum: int = 1, maximum: int = 5000) -> int:
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid parameter: {key}") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"invalid parameter: {key}")
    return value


def _line(key: str, title: str, values: Any, *, overlay: bool = False, color: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"name": key, "title": title, "type": "line", "data": _clean(values), "overlay": overlay}
    if color:
        item["color"] = color
    return item


def _number(
    params: Mapping[str, Any],
    key: str,
    default: float,
    minimum: float = 0.000001,
    maximum: float = 1_000_000.0,
) -> float:
    try:
        value = float(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid parameter: {key}") from exc
    if not np.isfinite(value) or value < minimum or value > maximum:
        raise ValueError(f"invalid parameter: {key}")
    return value


def _output(name: str, plots: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "plots": plots, "signals": [], "layers": []}


def _rsi_series(values: pd.Series, period: int) -> pd.Series:
    """Compute Wilder RSI after a full period of actual price changes."""
    delta = pd.to_numeric(values, errors="coerce").diff()
    avg_gain = _wilder(delta.clip(lower=0), period)
    avg_loss = _wilder((-delta.clip(upper=0)), period)
    relative_strength = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - 100 / (1 + relative_strength)
    result = result.mask((avg_loss == 0) & (avg_gain > 0), 100)
    return result.mask((avg_loss == 0) & (avg_gain == 0), 0)


def _sar_rate(params: Mapping[str, Any], key: str, default_percent: float) -> float:
    value = _number(params, key, default_percent, minimum=0.000001, maximum=100)
    return value / 100 if value > 1 else value


def _series(df: pd.DataFrame, key: str) -> pd.Series:
    return pd.to_numeric(df[key], errors="coerce")


def _wilder(values: pd.Series, period: int) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    finite = pd.to_numeric(values, errors="coerce")
    valid_positions = np.flatnonzero(np.isfinite(finite.to_numpy(dtype=float, copy=False)))
    if len(valid_positions) < period:
        return result
    seed_end_pos = valid_positions[period - 1]
    seed = finite.iloc[valid_positions[:period]].mean()
    if not np.isfinite(seed):
        return result
    result.iloc[seed_end_pos] = seed
    for index in range(seed_end_pos + 1, len(finite)):
        current = finite.iloc[index]
        previous = result.iloc[index - 1]
        result.iloc[index] = previous if not np.isfinite(current) else (previous * (period - 1) + current) / period
    return result


def _wma(values: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / weights.sum()), raw=True
    )
