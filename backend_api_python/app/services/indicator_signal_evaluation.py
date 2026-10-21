"""Pure signal selection for indicator alert workflows."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import numpy as np


_FALSE_SIGNAL_STRINGS = {"", "0", "false", "none", "null", "nan", "na", "n/a"}


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _signal_marker_is_active(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, dict):
        for key in ("active", "signal", "triggered", "hit", "visible"):
            if key in value and value.get(key) is not None:
                return _signal_marker_is_active(value.get(key))
        return any(key in value and _signal_marker_is_active(value.get(key)) for key in ("price", "value", "y", "data"))
    try:
        if pd.isna(value):
            return False
    except Exception:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _FALSE_SIGNAL_STRINGS
    try:
        number = float(value)
        return math.isfinite(number) and number != 0
    except (TypeError, ValueError):
        return False


def _signal_marker_price(value: Any, fallback: float) -> float:
    if isinstance(value, dict):
        for key in ("price", "value", "y", "data"):
            if key in value:
                return _safe_float(value.get(key), fallback)
        return fallback
    if isinstance(value, (bool, np.bool_)):
        return fallback
    return _safe_float(value, fallback)


def _signal_render_mode(signal: Dict[str, Any], data: List[Any]) -> str:
    raw_mode = str(signal.get("renderMode") or signal.get("mode") or "").strip().lower()
    if raw_mode in ("event", "events"):
        return "events"
    if raw_mode in ("point", "points", "marker", "markers", "raw"):
        return "points"
    if raw_mode in ("state", "continuous", "condition"):
        return "edge"
    if not data:
        return "events"
    active_count = sum(1 for value in data if _signal_marker_is_active(value))
    return "edge" if active_count / len(data) > 0.18 else "events"


def _signal_marker_should_notify(signal: Dict[str, Any], data: List[Any], idx: int) -> bool:
    if idx < 0 or idx >= len(data) or not _signal_marker_is_active(data[idx]):
        return False
    if _signal_render_mode(signal, data) != "edge":
        return True
    return idx == 0 or not _signal_marker_is_active(data[idx - 1])


def _signal_side(label: Any, signal_type: Any) -> str:
    text = f"{label or ''} {signal_type or ''}".strip().lower()
    if any(token in text for token in ("buy", "long", "cross up", "enter", "一买", "二买", "三买")):
        return "buy"
    if any(token in text for token in ("sell", "short", "cross down", "exit", "一卖", "二卖", "三卖")):
        return "sell"
    if "watch" in text or "observe" in text:
        return "watch"
    return "signal"


def _bar_time(value: Any, index: int) -> str:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None).isoformat()
        except Exception:
            return str(value)
    return str(value or index)


def matches_selected_signal(selected: set[str], signal_type: str, label: str) -> bool:
    if "any" in selected:
        return True
    signal_key = signal_type.strip().lower()
    label_key = label.strip().lower()
    return bool(selected.intersection({f"type:{signal_key}", f"text:{label_key}", f"signal:{signal_key}", label_key, signal_key}))


def latest_matching_signal(
    output: Dict[str, Any],
    frame: pd.DataFrame,
    keys: List[str],
    matches: Callable[[set[str], str, str], bool] = matches_selected_signal,
) -> Optional[Dict[str, Any]]:
    """Select a marker on the last closed bar for next-bar delivery."""
    signals = output.get("signals") or []
    if not isinstance(signals, list) or frame.empty or len(frame) < 2:
        return None
    index = len(frame) - 2
    notify_index = len(frame) - 1
    bar = frame.iloc[index]
    notify_bar = frame.iloc[notify_index]
    selected = {_normalize_key(key) for key in (keys or ["any"])}
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        data = signal.get("data") if isinstance(signal.get("data"), list) else []
        text_data = signal.get("textData") if isinstance(signal.get("textData"), list) else []
        marker = data[index] if index < len(data) else None
        point_text = text_data[index] if index < len(text_data) else None
        if not _signal_marker_should_notify(signal, data, index):
            continue
        signal_type = str(signal.get("type") or "signal").strip() or "signal"
        label = str(point_text or signal.get("text") or signal_type).strip()
        if not matches(selected, signal_type, label):
            continue
        return {
            "type": signal_type,
            "label": label,
            "price": _signal_marker_price(marker, _safe_float(bar.get("close"))),
            "bar_time": _bar_time(bar.get("time"), index),
            "bar_index": index,
            "notify_bar_time": _bar_time(notify_bar.get("time"), notify_index),
            "notify_bar_index": notify_index,
        }
    return None


def latest_series_condition(output: Dict[str, Any], frame: pd.DataFrame, condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Select a threshold crossing on the last closed bar."""
    plots = output.get("plots") if isinstance(output.get("plots"), list) else []
    if len(frame) < 3 or not plots:
        return None
    index = len(frame) - 2
    notify_index = len(frame) - 1
    operator = str(condition.get("operator") or "cross_above").strip().lower()
    threshold = _safe_float(condition.get("threshold"), 0.0)
    selected_key = str(condition.get("series_key") or "*").strip().lower()
    bar = frame.iloc[index]
    notify_bar = frame.iloc[notify_index]

    for plot in plots:
        if not isinstance(plot, dict):
            continue
        name = str(plot.get("name") or plot.get("key") or "value")
        if selected_key not in {"", "*", "any"} and name.strip().lower() != selected_key:
            continue
        values = plot.get("data") if isinstance(plot.get("data"), list) else []
        if index >= len(values) or index - 1 >= len(values):
            continue
        try:
            previous = float(values[index - 1])
            current = float(values[index])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(previous) or not math.isfinite(current):
            continue
        crossed_up = previous <= threshold and current > threshold
        crossed_down = previous >= threshold and current < threshold
        if (operator == "cross_above" and not crossed_up) or (operator == "cross_below" and not crossed_down):
            continue
        return {
            "type": operator,
            "label": f"{name} {operator.replace('_', ' ')} {threshold:g}",
            "price": _safe_float(bar.get("close")),
            "indicator_value": current,
            "series": name,
            "threshold": threshold,
            "bar_time": _bar_time(bar.get("time"), index),
            "bar_index": index,
            "notify_bar_time": _bar_time(notify_bar.get("time"), notify_index),
            "notify_bar_index": notify_index,
        }
    return None


def latest_chart_signal(signals: List[Dict[str, Any]], frame: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Return the newest visible marker for chart preview."""
    if frame.empty:
        return None
    for index in range(len(frame) - 1, -1, -1):
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            data = signal.get("data") if isinstance(signal.get("data"), list) else []
            marker = data[index] if index < len(data) else None
            if not _signal_marker_should_notify(signal, data, index):
                continue
            text_data = signal.get("textData") if isinstance(signal.get("textData"), list) else []
            point_text = text_data[index] if index < len(text_data) else None
            signal_type = str(signal.get("type") or "signal").strip() or "signal"
            bar = frame.iloc[index]
            return {
                "type": signal_type,
                "label": str(point_text or signal.get("text") or signal_type).strip(),
                "side": _signal_side(point_text or signal.get("text"), signal_type),
                "price": _signal_marker_price(marker, _safe_float(bar.get("close"))),
                "bar_time": _bar_time(bar.get("time"), index),
                "bar_index": index,
                "color": signal.get("color"),
            }
    return None
