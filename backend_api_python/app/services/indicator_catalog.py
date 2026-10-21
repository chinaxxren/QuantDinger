"""Unified server-side chart indicator catalog and aligned calculations.

The chart owns layout and rendering; this module owns indicator metadata and
the shared calculation contract. Each indicator's implementation lives in one
reviewed module under ``indicator_library/indicators``. The storage and
execution format is internal and does not create separate indicator catalogs.
Every returned series is aligned one-to-one with submitted OHLCV bars and uses
``None`` for warm-up or invalid values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
import inspect
import re
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from app.services.indicator_library.catalog import (
    get_indicator_compute,
    get_indicator_source_code,
)


ComputeFunc = Callable[[pd.DataFrame, Mapping[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ChartIndicatorDefinition:
    indicator_id: str
    name: str
    short_name: str
    indicator_type: str
    default_params: dict[str, Any]
    parameter_schema: list[dict[str, Any]]
    compute: ComputeFunc | None
    single_instance: bool = False
    alert_mode: str = "series"
    default_alert_condition: dict[str, Any] | None = None

    def metadata(self) -> dict[str, Any]:
        parameter_schema = []
        for field in self.parameter_schema:
            item = dict(field)
            if item.get("key") in self.default_params:
                default_value = self.default_params[item["key"]]
                item["defaultValue"] = default_value
                if item.get("type", "number") == "number" and "precision" not in item:
                    precision = max(
                        0,
                        -Decimal(str(default_value)).as_tuple().exponent,
                        -Decimal(str(item.get("step", 1))).as_tuple().exponent,
                    )
                    item["precision"] = precision
            parameter_schema.append(item)
        compute_available = self.compute is not None or get_indicator_compute(self.indicator_id) is not None
        alert_mode = (
            "none"
            if self.alert_mode == "none"
            else ("markers" if _has_explicit_signal_output(self.indicator_id, self.compute) else "series")
        )
        metadata = {
            "id": self.indicator_id,
            "name": self.name,
            "shortName": self.short_name,
            # Keep frontend layout/interaction code intact: this only changes the
            # calculation source, not the chart controls or pane placement.
            "type": "backend",
            "indicatorType": self.indicator_type,
            "defaultParams": dict(self.default_params),
            "paramSchema": parameter_schema,
            # Keep the catalog honest: a chart definition is usable for alerts
            # only when the server has a reviewed calculation for it.
            "computeAvailable": compute_available,
            "signalMode": alert_mode,
            "signalCapable": compute_available and alert_mode != "none",
            "defaultAlertCondition": self.default_alert_condition
            or {
                "operator": "cross_above",
                "threshold": 0,
                "series_key": "*",
            },
        }
        if self.single_instance:
            metadata["singleInstance"] = True
        return metadata


@lru_cache(maxsize=None)
def _has_explicit_signal_output(indicator_id: str, compute: ComputeFunc | None) -> bool:
    """Detect whether a reviewed implementation declares signal markers."""
    try:
        source = get_indicator_source_code(indicator_id) or ""
        if not source and compute is not None:
            source = inspect.getsource(compute)
        if not source:
            return False
    except (OSError, TypeError):
        return False
    return re.search(r"[\"']signals[\"']\s*:\s*\[\s*(?!\])", source) is not None


def _normalize_indicator_params(definition: ChartIndicatorDefinition, params: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(params)
    for field in definition.parameter_schema:
        key = field["key"]
        if key not in params:
            continue
        value = params[key]
        field_type = field.get("type", "number")
        if field_type == "number":
            if isinstance(value, bool):
                raise ValueError(f"invalid parameter: {key}")
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid parameter: {key}") from exc
            if not np.isfinite(number):
                raise ValueError(f"invalid parameter: {key}")
            if number < field.get("min", number) or number > field.get("max", number):
                raise ValueError(f"invalid parameter: {key}")
            if isinstance(definition.default_params.get(key), int):
                if not number.is_integer():
                    raise ValueError(f"invalid parameter: {key}")
                normalized[key] = int(number)
            else:
                normalized[key] = number
        elif field_type in {"bool", "boolean"}:
            if isinstance(value, bool):
                normalized[key] = value
            elif isinstance(value, (str, int)):
                text = str(value).strip().lower()
                if text not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
                    raise ValueError(f"invalid parameter: {key}")
                normalized[key] = text in {"true", "1", "yes", "on"}
            else:
                raise ValueError(f"invalid parameter: {key}")
        elif field_type in {"string", "str"} and field.get("options"):
            if value not in field["options"]:
                raise ValueError(f"invalid parameter: {key}")
        elif field_type == "color":
            if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
                raise ValueError(f"invalid parameter: {key}")
    ordered_periods = {
        "macd_leader": ("short_length", "long_length"),
        "macd_bollinger_bands": ("fast_length", "slow_length"),
        "volume_weighted_macd": ("fast_length", "slow_length"),
        "itg_scalper": ("fast_length", "slow_length"),
        "delta_rsi_oscillator": ("fast_period", "slow_period"),
        "powertrend_volume_range_filter": ("fast_period", "slow_period"),
        "pvo": ("short_period", "long_period"),
    }
    pair = ordered_periods.get(definition.indicator_id)
    if pair and normalized[pair[0]] >= normalized[pair[1]]:
        raise ValueError(f"invalid parameter: {pair[1]}")
    if definition.indicator_id == "auto_chart_patterns" and normalized["min_pivots"] > normalized["max_pivots"]:
        raise ValueError("invalid parameter: max_pivots")
    if definition.indicator_id == "trading_abc" and normalized["fibodn"] >= normalized["fiboup"]:
        raise ValueError("invalid parameter: fiboup")
    if definition.indicator_id == "machine_learning_rsi" and normalized["oversold"] >= normalized["overbought"]:
        raise ValueError("invalid parameter: overbought")
    return normalized


def _normalize_indicator_result(
    definition: ChartIndicatorDefinition,
    frame: pd.DataFrame,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize the common chart result contract for every indicator."""
    result = dict(result)
    plots = []
    for index, raw_plot in enumerate(result.get("plots") or []):
        if not isinstance(raw_plot, Mapping):
            continue
        plot = dict(raw_plot)
        title = str(plot.get("title") or plot.get("name") or f"Plot {index + 1}")
        key = str(plot.get("key") or plot.get("name") or f"plot_{index + 1}")
        plot["name"] = key
        plot["title"] = title
        plot["type"] = plot.get("type") or ("histogram" if "histogram" in f"{key} {title}".lower() else "line")
        if "lineWidth" not in plot:
            if "width" in plot:
                plot["lineWidth"] = plot["width"]
            elif "linewidth" in plot:
                plot["lineWidth"] = plot["linewidth"]
        plot_data = plot.get("data")
        plot["data"] = _clean([] if plot_data is None else plot_data)
        if len(plot["data"]) != len(frame):
            raise RuntimeError("indicator source returned unaligned plot data")
        plots.append(plot)

    signals = []
    for signal in result.get("signals") or []:
        if not isinstance(signal, Mapping):
            continue
        normalized = dict(signal)
        signal_data = normalized.get("data")
        normalized["data"] = _clean([] if signal_data is None else signal_data)
        if len(normalized["data"]) != len(frame):
            raise RuntimeError("indicator source returned unaligned signal data")
        signals.append(normalized)

    result["name"] = definition.name
    result["plots"] = plots
    result["signals"] = signals
    result.setdefault("layers", [])
    return result


def _integer(params: Mapping[str, Any], key: str, default: int, minimum: int = 1, maximum: int = 5000) -> int:
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid parameter: {key}") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"invalid parameter: {key}")
    return value


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


def _line(key: str, title: str, values: Any, *, overlay: bool = False, color: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"name": key, "title": title, "type": "line", "data": _clean(values), "overlay": overlay}
    if color:
        item["color"] = color
    return item


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


def _output(name: str, plots: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "plots": plots, "signals": [], "layers": []}


def _series(df: pd.DataFrame, key: str) -> pd.Series:
    return pd.to_numeric(df[key], errors="coerce")


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


def _rsi_series(values: pd.Series, period: int) -> pd.Series:
    """Compute Wilder RSI after a full period of actual price changes."""
    delta = pd.to_numeric(values, errors="coerce").diff()
    avg_gain = _wilder(delta.clip(lower=0), period)
    avg_loss = _wilder((-delta.clip(upper=0)), period)
    relative_strength = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - 100 / (1 + relative_strength)
    result = result.mask((avg_loss == 0) & (avg_gain > 0), 100)
    return result.mask((avg_loss == 0) & (avg_gain == 0), 0)


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous = close.shift(1)
    tr = pd.concat([high - low, (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1)
    return _wilder(tr, period)


def _wma(values: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / weights.sum()), raw=True
    )


def _sar_rate(params: Mapping[str, Any], key: str, default_percent: float) -> float:
    value = _number(params, key, default_percent, minimum=0.000001, maximum=100)
    return value / 100 if value > 1 else value


_SCHEMA_PERIOD = {"type": "number", "min": 1, "max": 500, "step": 1}


def _period_schema(key: str = "length", *, maximum: int = 500) -> list[dict[str, Any]]:
    return [{"key": key, "labelKey": "indicatorIde.editor.period", **{**_SCHEMA_PERIOD, "max": maximum}}]


def _number_schema(
    key: str,
    minimum: float,
    maximum: float,
    step: float = 1,
    *,
    precision: int | None = None,
    label_key: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"key": key, "type": "number", "min": minimum, "max": maximum, "step": step}
    if label_key:
        item["labelKey"] = label_key
    if precision is not None:
        item["precision"] = precision
    return item


def _load_indicator_compute(indicator_id: str) -> ComputeFunc:
    """Load the canonical compute entry point for one indicator module."""
    calculation = get_indicator_compute(indicator_id)
    if not callable(calculation):
        raise RuntimeError(f"Missing calculation for indicator: {indicator_id}")
    return calculation


_ad = _load_indicator_compute("ad")
_adosc = _load_indicator_compute("adosc")
_adx = _load_indicator_compute("adx")
_aroon = _load_indicator_compute("aroon")
_atr_indicator = _load_indicator_compute("atr")
_atr_rope = _load_indicator_compute("atr_rope")
_atr_trailing_stop = _load_indicator_compute("atr_trailing_stop")
_bias = _load_indicator_compute("bias")
_bollinger = _load_indicator_compute("bb")
_bop = _load_indicator_compute("bop")
_cci = _load_indicator_compute("cci")
_chaikin_oscillator = _load_indicator_compute("chaikin_oscillator")
_chandelier = _load_indicator_compute("chandelier_exit")
_chip_distribution = _load_indicator_compute("chip_distribution")
_choppiness = _load_indicator_compute("choppiness")
_cmf = _load_indicator_compute("cmf")
_cmo = _load_indicator_compute("cmo")
_connors_rsi = _load_indicator_compute("connors_rsi")
_coppock = _load_indicator_compute("coppock")
_dema = _load_indicator_compute("dema")
_donchian = _load_indicator_compute("donchian")
_dpo = _load_indicator_compute("dpo")
_ease_of_movement = _load_indicator_compute("ease_of_movement")
_elder_ray = _load_indicator_compute("elder_ray")
_ema_indicator = _load_indicator_compute("ema")
_fisher = _load_indicator_compute("fisher")
_force_index = _load_indicator_compute("force_index")
_gaussian_trend = _load_indicator_compute("gaussian_trend")
_half_trend = _load_indicator_compute("half_trend")
_hma = _load_indicator_compute("hma")
_ichimoku = _load_indicator_compute("ichimoku")
_kama = _load_indicator_compute("kama")
_kdj = _load_indicator_compute("kdj")
_keltner = _load_indicator_compute("keltner")
_klinger = _load_indicator_compute("klinger")
_macd = _load_indicator_compute("macd")
_mass_index = _load_indicator_compute("mass_index")
_mfi = _load_indicator_compute("mfi")
_momentum = _load_indicator_compute("mtm")
_nrtr = _load_indicator_compute("nrtr")
_obv = _load_indicator_compute("obv")
_pmax = _load_indicator_compute("pmax")
_ppo = _load_indicator_compute("ppo")
_pvt = _load_indicator_compute("pvt")
_qqe = _load_indicator_compute("qqe")
_range_filter = _load_indicator_compute("range_filter")
_rmi = _load_indicator_compute("rmi_trend")
_roc = _load_indicator_compute("roc")
_rsi = _load_indicator_compute("rsi")
_rvi = _load_indicator_compute("rvi")
_rvi_volatility = _load_indicator_compute("relative_volatility")
_sar = _load_indicator_compute("sar")
_sma = _load_indicator_compute("sma")
_stc = _load_indicator_compute("stc")
_stochastic = _load_indicator_compute("stochastic")
_stochastic_rsi = _load_indicator_compute("stochastic_rsi")
_super_bollinger = _load_indicator_compute("super_bollinger")
_supertrend = _load_indicator_compute("supertrend")
_trend_state = _load_indicator_compute("trend_state")
_trix = _load_indicator_compute("trix")
_tsi = _load_indicator_compute("tsi")
_turtle = _load_indicator_compute("turtle_channels")
_ulcer_index = _load_indicator_compute("ulcer_index")
_ultimate_oscillator = _load_indicator_compute("ultimate_oscillator")
_vidya = _load_indicator_compute("vidya")
_volume_macd = _load_indicator_compute("volume_macd")
_volume_oscillator = _load_indicator_compute("volume_oscillator")
_vortex = _load_indicator_compute("vortex")
_vwap = _load_indicator_compute("vwap")
_vwap_channel = _load_indicator_compute("vwap_channel")
_williams = _load_indicator_compute("williams")
_zero_lag_trend = _load_indicator_compute("zero_lag_trend")


def _make_definitions() -> dict[str, ChartIndicatorDefinition]:
    defs = [
        ChartIndicatorDefinition("sma", "SMA", "SMA", "line", {"length": 20}, _period_schema(maximum=300), _sma),
        ChartIndicatorDefinition(
            "ema", "EMA", "EMA", "line", {"length": 20}, _period_schema(maximum=300), _ema_indicator
        ),
        ChartIndicatorDefinition("rsi", "RSI", "RSI", "line", {"length": 14}, _period_schema(maximum=200), _rsi),
        ChartIndicatorDefinition(
            "macd",
            "MACD",
            "MACD",
            "macd",
            {"fast": 12, "slow": 26, "signal": 9},
            [
                {
                    "key": "fast",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal",
                    "labelKey": "indicatorIde.editor.signalLine",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            _macd,
        ),
        ChartIndicatorDefinition(
            "bb",
            "Bollinger Bands",
            "BB",
            "band",
            {"length": 20, "mult": 2},
            _period_schema(maximum=300)
            + [
                {
                    "key": "mult",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            _bollinger,
        ),
        ChartIndicatorDefinition(
            "atr", "ATR", "ATR", "line", {"period": 14}, _period_schema("period", maximum=200), _atr_indicator
        ),
        ChartIndicatorDefinition(
            "cci",
            "CCI",
            "CCI",
            "line",
            {"length": 20},
            _period_schema(maximum=200),
            _cci,
            default_alert_condition={"operator": "cross_above", "threshold": 100, "series_key": "*"},
        ),
        ChartIndicatorDefinition(
            "williams", "Williams %R", "W%R", "line", {"length": 14}, _period_schema(maximum=200), _williams
        ),
        ChartIndicatorDefinition("mfi", "MFI", "MFI", "line", {"length": 14}, _period_schema(maximum=200), _mfi),
        ChartIndicatorDefinition("adx", "ADX", "ADX", "adx", {"length": 14}, _period_schema(maximum=200), _adx),
        ChartIndicatorDefinition("obv", "OBV", "OBV", "line", {}, [], _obv),
        ChartIndicatorDefinition(
            "adosc",
            "ADOSC",
            "ADOSC",
            "line",
            {"fast": 3, "slow": 10},
            [
                {
                    "key": "fast",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _adosc,
        ),
        ChartIndicatorDefinition("ad", "AD", "AD", "line", {}, [], _ad),
        ChartIndicatorDefinition(
            "kdj",
            "KDJ",
            "KDJ",
            "line",
            {"period": 9, "k": 3, "d": 3},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "k",
                    "labelKey": "indicatorIde.editor.kSmoothing",
                    "type": "number",
                    "min": 1,
                    "max": 20,
                    "step": 1,
                },
                {
                    "key": "d",
                    "labelKey": "indicatorIde.editor.dSmoothing",
                    "type": "number",
                    "min": 1,
                    "max": 20,
                    "step": 1,
                },
            ],
            _kdj,
        ),
        ChartIndicatorDefinition(
            "vwap", "Volume Weighted Average Price", "VWAP", "line", {"period": 20}, _period_schema("period"), _vwap
        ),
        ChartIndicatorDefinition(
            "sar",
            "Parabolic SAR",
            "SAR",
            "native",
            {"start": 2, "step": 2, "max": 20},
            [
                _number_schema("start", 0.1, 20, 0.1, precision=1, label_key="indicatorIde.editor.sarStart"),
                _number_schema("step", 0.1, 20, 0.1, precision=1, label_key="indicatorIde.editor.sarStep"),
                _number_schema("max", 1, 100, 1, label_key="indicatorIde.editor.sarMaximum"),
            ],
            _sar,
            True,
        ),
        ChartIndicatorDefinition(
            "roc",
            "Rate of Change",
            "ROC",
            "native",
            {"period": 12, "smoothing": 6},
            _period_schema("period", maximum=300)
            + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")],
            _roc,
            True,
        ),
        ChartIndicatorDefinition(
            "mtm",
            "Momentum",
            "MTM",
            "native",
            {"period": 12, "smoothing": 6},
            _period_schema("period", maximum=300)
            + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")],
            _momentum,
            True,
        ),
        ChartIndicatorDefinition(
            "bias",
            "Bias Ratio",
            "BIAS",
            "native",
            {"short": 6, "medium": 12, "long": 24},
            [
                _number_schema("short", 1, 100, 1, label_key="indicatorIde.editor.shortPeriod"),
                _number_schema("medium", 2, 200, 1, label_key="indicatorIde.editor.mediumPeriod"),
                _number_schema("long", 3, 500, 1, label_key="indicatorIde.editor.longPeriod"),
            ],
            _bias,
            True,
        ),
        ChartIndicatorDefinition(
            "trix",
            "Triple Exponential Average",
            "TRIX",
            "native",
            {"period": 12, "smoothing": 9},
            _period_schema("period", maximum=300)
            + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")],
            _trix,
            True,
        ),
        ChartIndicatorDefinition(
            "supertrend",
            "SuperTrend",
            "SuperTrend",
            "line",
            {"period": 10, "multiplier": 3.0},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            _supertrend,
        ),
        ChartIndicatorDefinition(
            "aroon",
            "Aroon Oscillator",
            "Aroon",
            "line",
            {"period": 25},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _aroon,
        ),
        ChartIndicatorDefinition(
            "stochastic",
            "Stochastic Oscillator",
            "Stoch",
            "line",
            {"length": 14, "smooth_k": 3, "smooth_d": 3},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "smooth_k",
                    "labelKey": "indicatorIde.editor.kSmoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "smooth_d",
                    "labelKey": "indicatorIde.editor.dSmoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
            ],
            _stochastic,
        ),
        ChartIndicatorDefinition(
            "stochastic_rsi",
            "Stochastic RSI",
            "Stoch RSI",
            "line",
            {"rsi_period": 14, "stochastic_period": 14, "k_period": 3, "d_period": 3},
            [
                {
                    "key": "rsi_period",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "stochastic_period",
                    "labelKey": "indicatorIde.editor.stochasticPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "k_period",
                    "labelKey": "indicatorIde.editor.kPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "d_period",
                    "labelKey": "indicatorIde.editor.dPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
            ],
            _stochastic_rsi,
        ),
        ChartIndicatorDefinition(
            "donchian",
            "Donchian Channel",
            "Donchian",
            "band",
            {"length": 20},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _donchian,
        ),
        ChartIndicatorDefinition(
            "keltner",
            "Keltner Channel",
            "Keltner",
            "band",
            {"period": 20, "atr_period": 10, "multiplier": 2.0},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 8,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _keltner,
        ),
        ChartIndicatorDefinition(
            "ichimoku",
            "Ichimoku Cloud",
            "Ichimoku",
            "band",
            {"conversion_period": 9, "base_period": 26, "span_b_period": 52},
            [
                {
                    "key": "conversion_period",
                    "labelKey": "indicatorIde.editor.conversionPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "base_period",
                    "labelKey": "indicatorIde.editor.basePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "span_b_period",
                    "labelKey": "indicatorIde.editor.spanBPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
            ],
            _ichimoku,
        ),
        ChartIndicatorDefinition(
            "cmf",
            "Chaikin Money Flow",
            "CMF",
            "line",
            {"period": 20},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _cmf,
        ),
        ChartIndicatorDefinition(
            "cmo",
            "Chande Momentum Oscillator",
            "CMO",
            "line",
            {"period": 14},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _cmo,
        ),
        ChartIndicatorDefinition(
            "dema",
            "Double Exponential Moving Average",
            "DEMA",
            "line",
            {"period": 20},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
            ],
            _dema,
        ),
        ChartIndicatorDefinition(
            "hma",
            "Hull Moving Average",
            "HMA",
            "line",
            {"period": 20},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
            ],
            _hma,
        ),
        ChartIndicatorDefinition(
            "vortex",
            "Vortex Indicator",
            "Vortex",
            "line",
            {"period": 14},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _vortex,
        ),
        ChartIndicatorDefinition(
            "ultimate_oscillator",
            "Ultimate Oscillator",
            "UO",
            "line",
            {"short_period": 7, "medium_period": 14, "long_period": 28},
            [
                {
                    "key": "short_period",
                    "labelKey": "indicatorIde.editor.shortPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "medium_period",
                    "labelKey": "indicatorIde.editor.mediumPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 150,
                    "step": 1,
                },
                {
                    "key": "long_period",
                    "labelKey": "indicatorIde.editor.longPeriod",
                    "type": "number",
                    "min": 4,
                    "max": 250,
                    "step": 1,
                },
            ],
            _ultimate_oscillator,
        ),
        ChartIndicatorDefinition(
            "fisher",
            "Fisher Transform",
            "Fisher",
            "line",
            {"period": 10, "signal_period": 1},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
            ],
            _fisher,
        ),
        ChartIndicatorDefinition(
            "force_index",
            "Force Index",
            "Force",
            "line",
            {"period": 13},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
            ],
            _force_index,
        ),
        ChartIndicatorDefinition(
            "ease_of_movement",
            "Ease of Movement",
            "EOM",
            "line",
            {"period": 14, "volume_divisor": 10000.0},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "volume_divisor",
                    "labelKey": "indicatorIde.editor.volumeDivisor",
                    "type": "number",
                    "min": 1,
                    "max": 1_000_000_000,
                    "step": 1000,
                    "precision": 0,
                },
            ],
            _ease_of_movement,
        ),
        ChartIndicatorDefinition(
            "chaikin_oscillator",
            "Chaikin Oscillator",
            "Chaikin",
            "line",
            {"fast_period": 3, "slow_period": 10},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _chaikin_oscillator,
        ),
        ChartIndicatorDefinition(
            "volume_oscillator",
            "Volume Oscillator",
            "Volume Osc",
            "line",
            {"fast_period": 5, "slow_period": 20, "signal_period": 5},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            _volume_oscillator,
        ),
        ChartIndicatorDefinition(
            "pvt",
            "Price Volume Trend",
            "PVT",
            "line",
            {"signal_period": 21},
            [
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
            ],
            _pvt,
        ),
        ChartIndicatorDefinition(
            "rvi",
            "Relative Vigor Index",
            "RVI",
            "line",
            {"period": 10},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _rvi,
        ),
        ChartIndicatorDefinition(
            "choppiness",
            "Choppiness Index",
            "CHOP",
            "line",
            {"period": 14},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _choppiness,
        ),
        ChartIndicatorDefinition(
            "qqe",
            "QQE Signals",
            "QQE",
            "line",
            {"rsi_period": 14, "rsi_smoothing": 5, "qqe_factor": 4.236},
            [
                {
                    "key": "rsi_period",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "rsi_smoothing",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "qqe_factor",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.5,
                    "max": 10,
                    "step": 0.1,
                    "precision": 3,
                },
            ],
            _qqe,
        ),
        ChartIndicatorDefinition(
            "rmi_trend",
            "RMI Trend Sniper",
            "RMI Trend",
            "line",
            {"length": 14, "pmom": 66, "nmom": 30},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "pmom",
                    "labelKey": "indicatorIde.editor.positiveThreshold",
                    "type": "number",
                    "min": 50,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "nmom",
                    "labelKey": "indicatorIde.editor.negativeThreshold",
                    "type": "number",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                },
            ],
            _rmi,
        ),
        ChartIndicatorDefinition(
            "stc",
            "Schaff Trend Cycle",
            "STC",
            "line",
            {"fast_period": 23, "slow_period": 50, "cycle_period": 10, "smoothing": 0.5},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 150,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 250,
                    "step": 1,
                },
                {
                    "key": "cycle_period",
                    "labelKey": "indicatorIde.editor.cyclePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "smoothing",
                    "labelKey": "indicatorIde.editor.smoothingFactor",
                    "type": "number",
                    "min": 0.1,
                    "max": 1,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            _stc,
        ),
        ChartIndicatorDefinition(
            "tsi",
            "True Strength Index",
            "TSI",
            "line",
            {"long_period": 25, "short_period": 13, "signal_period": 7},
            [
                {
                    "key": "long_period",
                    "labelKey": "indicatorIde.editor.longPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "short_period",
                    "labelKey": "indicatorIde.editor.shortPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _tsi,
        ),
        ChartIndicatorDefinition(
            "connors_rsi",
            "Connors RSI",
            "CRSI",
            "line",
            {"rsi_period": 3, "streak_rsi_period": 2, "rank_period": 100},
            [
                {
                    "key": "rsi_period",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "streak_rsi_period",
                    "labelKey": "indicatorIde.editor.streakRsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "rank_period",
                    "labelKey": "indicatorIde.editor.rankPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
            ],
            _connors_rsi,
        ),
        ChartIndicatorDefinition(
            "coppock",
            "Coppock Curve",
            "Coppock",
            "line",
            {"long_roc": 14, "short_roc": 11, "wma_period": 10},
            [
                {
                    "key": "long_roc",
                    "labelKey": "indicatorIde.editor.longPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "short_roc",
                    "labelKey": "indicatorIde.editor.shortPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "wma_period",
                    "labelKey": "indicatorIde.editor.wmaPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _coppock,
        ),
        ChartIndicatorDefinition(
            "dpo",
            "Detrended Price Oscillator",
            "DPO",
            "line",
            {"period": 20},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _dpo,
        ),
        ChartIndicatorDefinition(
            "mass_index",
            "Mass Index",
            "Mass",
            "line",
            {"ema_period": 9, "sum_period": 25},
            [
                {
                    "key": "ema_period",
                    "labelKey": "indicatorIde.editor.emaPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "sum_period",
                    "labelKey": "indicatorIde.editor.sumPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _mass_index,
        ),
        ChartIndicatorDefinition(
            "ulcer_index",
            "Ulcer Index",
            "Ulcer",
            "line",
            {"period": 14},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _ulcer_index,
        ),
        ChartIndicatorDefinition(
            "klinger",
            "Klinger Volume Oscillator",
            "KVO",
            "line",
            {"fast_period": 34, "slow_period": 55, "signal_period": 13},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 250,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _klinger,
        ),
        ChartIndicatorDefinition(
            "ppo",
            "Percentage Price Oscillator",
            "PPO",
            "line",
            {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _ppo,
        ),
        ChartIndicatorDefinition(
            "volume_macd",
            "Volume Weighted MACD",
            "VW MACD",
            "line",
            {"fast_length": 12, "slow_length": 26, "signal_length": 9, "histogram": True},
            [
                {
                    "key": "fast_length",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_length",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_length",
                    "labelKey": "indicatorIde.editor.signalLine",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "histogram", "labelKey": "indicatorIde.editor.showHistogram", "type": "bool"},
            ],
            _volume_macd,
        ),
        ChartIndicatorDefinition(
            "bop",
            "Balance of Power",
            "BOP",
            "line",
            {"smooth_period": 1},
            [
                {
                    "key": "smooth_period",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            _bop,
        ),
        ChartIndicatorDefinition(
            "relative_volatility",
            "Relative Volatility Index",
            "RVI",
            "line",
            {"period": 14},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _rvi_volatility,
        ),
        ChartIndicatorDefinition(
            "elder_ray",
            "Elder Ray Index",
            "Elder Ray",
            "line",
            {"period": 13},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _elder_ray,
        ),
        ChartIndicatorDefinition(
            "kama",
            "Kaufman Adaptive Moving Average",
            "KAMA",
            "line",
            {"period": 10, "fast_period": 2, "slow_period": 30},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
            ],
            _kama,
        ),
        ChartIndicatorDefinition(
            "vidya",
            "Variable Moving Average",
            "VIDYA",
            "line",
            {"period": 20, "momentum_period": 9, "signal_period": 9},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "momentum_period",
                    "labelKey": "indicatorIde.editor.momentumPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            _vidya,
        ),
        ChartIndicatorDefinition(
            "half_trend",
            "HalfTrend",
            "HalfTrend",
            "band",
            {"amplitude": 2, "atr_period": 100, "channel_deviation": 2.0},
            [
                {
                    "key": "amplitude",
                    "labelKey": "indicatorIde.editor.amplitude",
                    "type": "number",
                    "min": 1,
                    "max": 30,
                    "step": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "channel_deviation",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 6,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _half_trend,
        ),
        ChartIndicatorDefinition(
            "gaussian_trend",
            "Gaussian Filter Trend",
            "Gaussian",
            "band",
            {"period": 20, "poles": 3, "atr_period": 14, "multiplier": 1.5},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "poles",
                    "labelKey": "indicatorIde.editor.poles",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 8,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _gaussian_trend,
        ),
        ChartIndicatorDefinition(
            "atr_trailing_stop",
            "ATR Trailing Stop",
            "ATR Stop",
            "band",
            {"atr_length": 14, "atr_multiplier": 3.0, "source": "close"},
            [
                {
                    "key": "atr_length",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "atr_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.5,
                    "max": 8,
                    "step": 0.1,
                    "precision": 1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2"],
                },
            ],
            _atr_trailing_stop,
        ),
        ChartIndicatorDefinition(
            "chandelier_exit",
            "Chandelier Exit",
            "Chandelier",
            "line",
            {"length": 22, "atr_multiplier": 3.0},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 5,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "atr_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _chandelier,
        ),
        ChartIndicatorDefinition(
            "atr_rope",
            "ATR Rope",
            "ATR Rope",
            "line",
            {"atr_period": 14, "multiplier": 1.5},
            [
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 8,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _atr_rope,
        ),
        ChartIndicatorDefinition(
            "pmax",
            "PMax Trend Filter",
            "PMax",
            "line",
            {"ma_period": 10, "atr_period": 10, "atr_multiplier": 3.0},
            [
                {
                    "key": "ma_period",
                    "labelKey": "indicatorIde.editor.emaPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 60,
                    "step": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 60,
                    "step": 1,
                },
                {
                    "key": "atr_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _pmax,
        ),
        ChartIndicatorDefinition(
            "range_filter",
            "Range Filter",
            "Range Filter",
            "band",
            {"sampling_period": 50, "range_multiplier": 3.0},
            [
                {
                    "key": "sampling_period",
                    "labelKey": "indicatorIde.editor.samplingPeriod",
                    "type": "number",
                    "min": 10,
                    "max": 150,
                    "step": 5,
                },
                {
                    "key": "range_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _range_filter,
        ),
        ChartIndicatorDefinition(
            "vwap_channel",
            "VWAP Price Channel",
            "VWAP Channel",
            "band",
            {"period": 30, "deviation": 1.5},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "deviation",
                    "labelKey": "indicatorIde.editor.deviation",
                    "type": "number",
                    "min": 0.25,
                    "max": 5,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            _vwap_channel,
        ),
        ChartIndicatorDefinition(
            "turtle_channels",
            "Turtle Trade Channels",
            "Turtle",
            "band",
            {"entry_length": 20, "exit_length": 10},
            [
                {
                    "key": "entry_length",
                    "labelKey": "indicatorIde.editor.entryPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "exit_length",
                    "labelKey": "indicatorIde.editor.exitPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
            ],
            _turtle,
        ),
        ChartIndicatorDefinition(
            "nrtr",
            "NRTR",
            "NRTR",
            "line",
            {"percentage": 1.0, "mult": 0.0, "length": 20},
            [
                {
                    "key": "percentage",
                    "labelKey": "indicatorIde.editor.percentage",
                    "type": "number",
                    "min": 0.25,
                    "max": 5,
                    "step": 0.25,
                    "precision": 2,
                },
                {
                    "key": "mult",
                    "labelKey": "indicatorIde.editor.volatilityMultiplier",
                    "type": "number",
                    "min": 0,
                    "max": 3,
                    "step": 0.1,
                    "precision": 1,
                },
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 5,
                    "max": 100,
                    "step": 1,
                },
            ],
            _nrtr,
        ),
        ChartIndicatorDefinition(
            "trend_state",
            "Trend State Signals",
            "Trend State",
            "line",
            {"length": 20, "multiplier": 3.5, "src_type": "close"},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
                {
                    "key": "src_type",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
            ],
            _trend_state,
        ),
        ChartIndicatorDefinition(
            "zero_lag_trend",
            "Zero Lag Trend Signals",
            "Zero Lag",
            "band",
            {"length": 70, "mult": 1.2},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "mult",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            _zero_lag_trend,
        ),
        ChartIndicatorDefinition(
            "super_bollinger",
            "Super Bollinger Trend",
            "SBT",
            "band",
            {
                "prd": 12,
                "mult": 2.0,
                "show_zigzag": True,
                "signal": "Signal",
                "dev": "ZigZag",
                "show_tp": False,
                "tp_type": "Median",
            },
            [
                {
                    "key": "prd",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "mult",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
                {"key": "show_zigzag", "labelKey": "indicatorIde.editor.showZigzag", "type": "bool"},
                {
                    "key": "signal",
                    "labelKey": "indicatorIde.editor.signalMode",
                    "type": "string",
                    "options": ["Signal", "ZigZag"],
                },
                {
                    "key": "dev",
                    "labelKey": "indicatorIde.editor.deviationMode",
                    "type": "string",
                    "options": ["ZigZag", "Bollinger"],
                },
                {"key": "show_tp", "labelKey": "indicatorIde.editor.showTakeProfit", "type": "bool"},
                {
                    "key": "tp_type",
                    "labelKey": "indicatorIde.editor.takeProfitType",
                    "type": "string",
                    "options": ["Median", "Basis"],
                },
            ],
            _super_bollinger,
        ),
        ChartIndicatorDefinition(
            "alpha_trend",
            "AlphaTrend",
            "AlphaTrend",
            "line",
            {"atr_period": 14, "momentum_period": 14, "multiplier": 1.0, "confirmation_lag": 2},
            [
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "momentum_period",
                    "labelKey": "indicatorIde.editor.momentumPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 8,
                    "step": 0.25,
                },
                {
                    "key": "confirmation_lag",
                    "labelKey": "indicatorIde.editor.confirmationLag",
                    "type": "number",
                    "min": 1,
                    "max": 10,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "optimized_trend_tracker",
            "Optimized Trend Tracker",
            "OTT",
            "line",
            {"length": 2, "var_length": 9, "percent": 1.4, "base": 200},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "var_length",
                    "labelKey": "indicatorIde.editor.varLength",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "percent",
                    "labelKey": "indicatorIde.editor.percentage",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                },
                {
                    "key": "base",
                    "labelKey": "indicatorIde.editor.ottBase",
                    "type": "number",
                    "min": 10,
                    "max": 1000,
                    "step": 10,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "std_filtered_gaussian",
            "STD-Filtered N-Pole Gaussian Filter",
            "STD Gaussian",
            "line",
            {"period": 25, "poles": 5, "filter_period": 10, "filter_strength": 1.0},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "poles",
                    "labelKey": "indicatorIde.editor.poles",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 1,
                },
                {
                    "key": "filter_period",
                    "labelKey": "indicatorIde.editor.filterPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "filter_strength",
                    "labelKey": "indicatorIde.editor.filterStrength",
                    "type": "number",
                    "min": 0,
                    "max": 5,
                    "step": 0.25,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "adaptive_trend_filter",
            "Adaptive Trend Filter",
            "Adaptive Filter",
            "band",
            {"alpha_filter": 0.01, "beta_filter": 0.1, "filter_period": 21, "supertrend_factor": 1.0, "atr_period": 7},
            [
                {
                    "key": "alpha_filter",
                    "labelKey": "indicatorIde.editor.alphaFilter",
                    "type": "number",
                    "min": 0.001,
                    "max": 1,
                    "step": 0.001,
                },
                {
                    "key": "beta_filter",
                    "labelKey": "indicatorIde.editor.betaFilter",
                    "type": "number",
                    "min": 0.001,
                    "max": 2,
                    "step": 0.001,
                },
                {
                    "key": "filter_period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "supertrend_factor",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 8,
                    "step": 0.25,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "vegas_supertrend",
            "Multi-Step Vegas SuperTrend",
            "Vegas ST",
            "band",
            {"atr_period": 10, "vegas_period": 100, "supertrend_multiplier": 5.0, "volatility_adjustment": 5.0},
            [
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "vegas_period",
                    "labelKey": "indicatorIde.editor.vegasPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "supertrend_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.5,
                    "max": 12,
                    "step": 0.5,
                },
                {
                    "key": "volatility_adjustment",
                    "labelKey": "indicatorIde.editor.volatilityAdjustment",
                    "type": "number",
                    "min": 0,
                    "max": 20,
                    "step": 0.5,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "dsav",
            "DSAV Dynamic Swing Anchored VWAP",
            "DSAV",
            "line",
            {"prd": 50, "base_apt": 20, "use_adapt": False, "vol_bias": 10.0},
            [
                {
                    "key": "prd",
                    "labelKey": "indicatorIde.editor.swingPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "base_apt",
                    "labelKey": "indicatorIde.editor.halfLife",
                    "type": "number",
                    "min": 5,
                    "max": 300,
                    "step": 1,
                },
                {"key": "use_adapt", "labelKey": "indicatorIde.editor.useAdaptive", "type": "bool"},
                {
                    "key": "vol_bias",
                    "labelKey": "indicatorIde.editor.volatilityBias",
                    "type": "number",
                    "min": 0,
                    "max": 20,
                    "step": 0.5,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "lowess",
            "LOWESS Smoothing",
            "LOWESS",
            "band",
            {"length": 100, "malen": 100},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 10,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "malen",
                    "labelKey": "indicatorIde.editor.lowessPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "price_radio",
            "John Ehlers The Price Radio",
            "Price Radio",
            "line",
            {"am_period": 8, "fm_period": 30, "fm_gain": 10.0},
            [
                {
                    "key": "am_period",
                    "labelKey": "indicatorIde.editor.amPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "fm_period",
                    "labelKey": "indicatorIde.editor.fmPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "fm_gain",
                    "labelKey": "indicatorIde.editor.fmGain",
                    "type": "number",
                    "min": 0.1,
                    "max": 100,
                    "step": 0.1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "adaptive_trend_trail",
            "Adaptive Trend Trail",
            "ATT",
            "band",
            {
                "trend_length": 34,
                "momentum_length": 12,
                "sensitivity": 0.35,
                "st_fast_length": 9,
                "st_fast_factor": 1.45,
                "st_mid_length": 14,
                "st_mid_factor": 1.95,
                "st_slow_length": 21,
                "st_slow_factor": 2.55,
                "trail_size": 1.0,
                "smoothness": 5,
                "overlay_mode": "Trail",
            },
            [
                {
                    "key": "trend_length",
                    "labelKey": "indicatorIde.editor.trendPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "momentum_length",
                    "labelKey": "indicatorIde.editor.momentumPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "sensitivity",
                    "labelKey": "indicatorIde.editor.sensitivity",
                    "type": "number",
                    "min": 0,
                    "max": 1,
                    "step": 0.05,
                },
                {
                    "key": "st_fast_length",
                    "labelKey": "indicatorIde.editor.fastAtrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "st_fast_factor",
                    "labelKey": "indicatorIde.editor.fastAtrFactor",
                    "type": "number",
                    "min": 0.5,
                    "max": 5,
                    "step": 0.05,
                },
                {
                    "key": "st_mid_length",
                    "labelKey": "indicatorIde.editor.midAtrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "st_mid_factor",
                    "labelKey": "indicatorIde.editor.midAtrFactor",
                    "type": "number",
                    "min": 0.5,
                    "max": 6,
                    "step": 0.05,
                },
                {
                    "key": "st_slow_length",
                    "labelKey": "indicatorIde.editor.slowAtrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 150,
                    "step": 1,
                },
                {
                    "key": "st_slow_factor",
                    "labelKey": "indicatorIde.editor.slowAtrFactor",
                    "type": "number",
                    "min": 0.5,
                    "max": 8,
                    "step": 0.05,
                },
                {
                    "key": "trail_size",
                    "labelKey": "indicatorIde.editor.trailSize",
                    "type": "number",
                    "min": 0.5,
                    "max": 2,
                    "step": 0.05,
                },
                {
                    "key": "smoothness",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "overlay_mode",
                    "labelKey": "indicatorIde.editor.overlayMode",
                    "type": "string",
                    "options": ["Trail", "Bands", "None"],
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "spma_trend_nal",
            "SPMA Trend NAL",
            "SPMA",
            "band",
            {
                "source": "close",
                "baseline_length": 30,
                "percentrank_lookback": 30,
                "percentile_gate": 50.0,
                "use_asym_bands": False,
                "vol_method": "MeanAD",
                "vol_length": 14,
                "vol_multiple": 0.75,
                "quantile_pct": 90.0,
                "use_slope_gate": False,
                "slope_length": 10,
                "slope_gate": 0.5,
            },
            [
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "baseline_length",
                    "labelKey": "indicatorIde.editor.basePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "percentrank_lookback",
                    "labelKey": "indicatorIde.editor.percentRankPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "percentile_gate",
                    "labelKey": "indicatorIde.editor.percentileGate",
                    "type": "number",
                    "min": 0,
                    "max": 99,
                    "step": 1,
                },
                {"key": "use_asym_bands", "labelKey": "indicatorIde.editor.useAsymmetricBands", "type": "bool"},
                {
                    "key": "vol_length",
                    "labelKey": "indicatorIde.editor.volatilityPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "vol_multiple",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.05,
                    "max": 8,
                    "step": 0.05,
                },
                {
                    "key": "quantile_pct",
                    "labelKey": "indicatorIde.editor.quantilePercentile",
                    "type": "number",
                    "min": 50,
                    "max": 99,
                    "step": 1,
                },
                {"key": "use_slope_gate", "labelKey": "indicatorIde.editor.useSlopeGate", "type": "bool"},
                {
                    "key": "slope_length",
                    "labelKey": "indicatorIde.editor.slopePeriod",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slope_gate",
                    "labelKey": "indicatorIde.editor.slopeGate",
                    "type": "number",
                    "min": -20,
                    "max": 20,
                    "step": 0.1,
                },
                {
                    "key": "vol_method",
                    "labelKey": "indicatorIde.editor.volatilityMethod",
                    "type": "string",
                    "options": ["SD", "ATR", "MeanAD", "MedianAD", "Quantile"],
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "powertrend_volume_range_filter",
            "PowerTrend Volume Range Filter",
            "PowerTrend",
            "band",
            {
                "range_period": 34,
                "range_multiplier": 2.5,
                "fast_period": 21,
                "slow_period": 55,
                "volume_period": 34,
                "min_relative_volume": 1.05,
            },
            [
                {
                    "key": "range_period",
                    "labelKey": "indicatorIde.editor.rangePeriod",
                    "type": "number",
                    "min": 10,
                    "max": 120,
                    "step": 2,
                },
                {
                    "key": "range_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 1,
                    "max": 6,
                    "step": 0.25,
                    "precision": 2,
                },
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 5,
                    "max": 60,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 20,
                    "max": 160,
                    "step": 5,
                },
                {
                    "key": "volume_period",
                    "labelKey": "indicatorIde.editor.volumePeriod",
                    "type": "number",
                    "min": 10,
                    "max": 120,
                    "step": 2,
                },
                {
                    "key": "min_relative_volume",
                    "labelKey": "indicatorIde.editor.minRelativeVolume",
                    "type": "number",
                    "min": 0.5,
                    "max": 3,
                    "step": 0.05,
                    "precision": 2,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "g_channels",
            "G Channels",
            "G Channels",
            "band",
            {"length": 100, "signal_mode": "close"},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 20,
                    "max": 240,
                    "step": 5,
                },
                {
                    "key": "signal_mode",
                    "labelKey": "indicatorIde.editor.signalMode",
                    "type": "string",
                    "options": ["close", "channel"],
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "wavetrend_oscillator",
            "WaveTrend Oscillator",
            "WaveTrend",
            "line",
            {"channel_length": 10, "average_length": 21},
            [
                {
                    "key": "channel_length",
                    "labelKey": "indicatorIde.editor.channelPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 40,
                    "step": 1,
                },
                {
                    "key": "average_length",
                    "labelKey": "indicatorIde.editor.averagePeriod",
                    "type": "number",
                    "min": 3,
                    "max": 80,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "nadaraya_watson_envelope",
            "Nadaraya-Watson Envelope",
            "NW Envelope",
            "band",
            {"lookback": 64, "bandwidth": 8.0, "atr_period": 21, "envelope_multiplier": 2.0},
            [
                {
                    "key": "lookback",
                    "labelKey": "indicatorIde.editor.lookback",
                    "type": "number",
                    "min": 20,
                    "max": 160,
                    "step": 4,
                },
                {
                    "key": "bandwidth",
                    "labelKey": "indicatorIde.editor.bandwidth",
                    "type": "number",
                    "min": 2,
                    "max": 30,
                    "step": 0.5,
                    "precision": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 5,
                    "max": 80,
                    "step": 1,
                },
                {
                    "key": "envelope_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.5,
                    "max": 5,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "dynamic_linear_regression_channel",
            "Dynamic Linear Regression Channel",
            "Regression Channel",
            "band",
            {"period": 50, "deviation": 2.0},
            [
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 5,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "deviation",
                    "labelKey": "indicatorIde.editor.deviation",
                    "type": "number",
                    "min": 0.5,
                    "max": 4,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "ut_bot_alerts",
            "UT Bot Alerts",
            "UT Bot",
            "line",
            {"atr_period": 10, "key_value": 1.0},
            [
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "key_value",
                    "labelKey": "indicatorIde.editor.sensitivity",
                    "type": "number",
                    "min": 0.25,
                    "max": 10,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "twin_range_filter",
            "Twin Range Filter",
            "Twin Range",
            "line",
            {"source": "close", "per1": 27, "mult1": 1.6, "per2": 55, "mult2": 2.0},
            [
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "per1",
                    "labelKey": "indicatorIde.editor.fastPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "mult1",
                    "labelKey": "indicatorIde.editor.fastMultiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
                {
                    "key": "per2",
                    "labelKey": "indicatorIde.editor.slowPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "mult2",
                    "labelKey": "indicatorIde.editor.slowMultiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "pivot_point_supertrend",
            "Pivot Point Supertrend",
            "Pivot ST",
            "band",
            {"pivot_period": 2, "atr_period": 10, "multiplier": 3.0},
            [
                {
                    "key": "pivot_period",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 20,
                    "step": 1,
                },
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 10,
                    "step": 0.25,
                    "precision": 2,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "delta_rsi_oscillator",
            "Delta RSI Oscillator",
            "Delta RSI",
            "macd",
            {"fast_period": 7, "slow_period": 21, "signal_period": 5},
            [
                {
                    "key": "fast_period",
                    "labelKey": "indicatorIde.editor.fastRsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_period",
                    "labelKey": "indicatorIde.editor.slowRsiPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "range_filter_signals",
            "Range Filter B&S Signals",
            "Range Filter B&S",
            "band",
            {"rng_per": 20, "rng_qty": 3.5},
            [
                {
                    "key": "rng_per",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 150,
                    "step": 1,
                },
                {
                    "key": "rng_qty",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "know_sure_thing",
            "Know Sure Thing",
            "KST",
            "line",
            {"roc1_period": 10, "roc2_period": 15, "roc3_period": 20, "roc4_period": 30, "signal_period": 9},
            [
                {
                    "key": "roc1_period",
                    "labelKey": "indicatorIde.editor.roc1Period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "roc2_period",
                    "labelKey": "indicatorIde.editor.roc2Period",
                    "type": "number",
                    "min": 2,
                    "max": 150,
                    "step": 1,
                },
                {
                    "key": "roc3_period",
                    "labelKey": "indicatorIde.editor.roc3Period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "roc4_period",
                    "labelKey": "indicatorIde.editor.roc4Period",
                    "type": "number",
                    "min": 2,
                    "max": 250,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "macd_leader",
            "MACD Leader",
            "MACD Leader",
            "line",
            {
                "short_length": 12,
                "long_length": 26,
                "sig_length": 9,
                "show_macd": False,
                "show_macdsignal": False,
                "src": "close",
                "ema_seed": "sma",
            },
            [
                {
                    "key": "short_length",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "long_length",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 2,
                    "max": 500,
                    "step": 1,
                },
                {
                    "key": "sig_length",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
                {"key": "show_macd", "labelKey": "indicatorIde.editor.showMacd", "type": "bool"},
                {"key": "show_macdsignal", "labelKey": "indicatorIde.editor.showMacdSignal", "type": "bool"},
                {
                    "key": "src",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "ema_seed",
                    "labelKey": "indicatorIde.editor.emaSeed",
                    "type": "string",
                    "options": ["sma", "first"],
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "envelope_rsi_signals",
            "Envelope RSI Signals",
            "Envelope RSI",
            "line",
            {"rsi_length": 14, "envelope_length": 20, "envelope_multiplier": 1.5, "show_envelope": True},
            [
                {
                    "key": "rsi_length",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "envelope_length",
                    "labelKey": "indicatorIde.editor.envelopePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "envelope_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 5,
                    "step": 0.1,
                    "precision": 1,
                },
                {"key": "show_envelope", "labelKey": "indicatorIde.editor.showEnvelope", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "follow_line_indicator",
            "Follow Line Indicator",
            "Follow Line",
            "line",
            {"bb_period": 21, "bb_deviations": 1.0, "use_atr_filter": True, "atr_period": 5, "hide_labels": False},
            [
                {
                    "key": "bb_period",
                    "labelKey": "indicatorIde.editor.bollingerPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "bb_deviations",
                    "labelKey": "indicatorIde.editor.deviation",
                    "type": "number",
                    "min": 0.1,
                    "max": 5,
                    "step": 0.1,
                    "precision": 1,
                },
                {"key": "use_atr_filter", "labelKey": "indicatorIde.editor.useAtrFilter", "type": "bool"},
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "hide_labels", "labelKey": "indicatorIde.editor.hideLabels", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "exhaustion_levels",
            "Exhaustion Levels",
            "Exhaustion",
            "line",
            {"exhaustion_switch": True, "level_switch": True, "length": 40, "bars": 10, "thickness": 2},
            [
                {"key": "exhaustion_switch", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
                {"key": "level_switch", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "bars",
                    "labelKey": "indicatorIde.editor.exhaustionBars",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "thickness",
                    "labelKey": "indicatorIde.editor.lineWidth",
                    "type": "number",
                    "min": 1,
                    "max": 5,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "hema_trend_levels",
            "HEMA Trend Levels",
            "HEMA",
            "band",
            {"length": 50, "atr_length": 14, "atr_multiplier": 1.5, "source": "close", "show_levels": True},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "atr_length",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "atr_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                    "precision": 1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {"key": "show_levels", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "market_structure_oscillator",
            "Market Structure Oscillator",
            "Market Structure",
            "line",
            {"structure_length": 20, "signal_length": 5, "volume_length": 20, "show_signal": True},
            [
                {
                    "key": "structure_length",
                    "labelKey": "indicatorIde.editor.structurePeriod",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_length",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "volume_length",
                    "labelKey": "indicatorIde.editor.volumePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {"key": "show_signal", "labelKey": "indicatorIde.editor.showSignal", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "adaptive_supertrend",
            "Adaptive SuperTrend",
            "Adaptive ST",
            "band",
            {"atr_period": 10, "factor": 3.0, "tqi_period": 14, "smooth_period": 3},
            [
                {
                    "key": "atr_period",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "factor",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.25,
                    "max": 10,
                    "step": 0.25,
                },
                {
                    "key": "tqi_period",
                    "labelKey": "indicatorIde.editor.tqiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "smooth_period",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "elder_impulse_system",
            "Elder Impulse System",
            "Elder Impulse",
            "band",
            {"ema_length": 13, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
            [
                {
                    "key": "ema_length",
                    "labelKey": "indicatorIde.editor.emaPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "macd_fast",
                    "labelKey": "indicatorIde.editor.fastPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "macd_slow",
                    "labelKey": "indicatorIde.editor.slowPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "macd_signal",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "swing_failure_pattern",
            "Swing Failure Pattern",
            "SFP",
            "band",
            {
                "length": 5,
                "bullish": True,
                "bearish": True,
                "swing_lines": True,
                "confirm_lines": True,
                "sfp_labels": True,
                "bull_color": "#089981",
                "bear_color": "#f23645",
                "validation": "None",
                "percent": 25.0,
            },
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "bullish", "labelKey": "indicatorIde.editor.showBullish", "type": "bool"},
                {"key": "bearish", "labelKey": "indicatorIde.editor.showBearish", "type": "bool"},
                {"key": "swing_lines", "labelKey": "indicatorIde.editor.showSwingLevels", "type": "bool"},
                {"key": "confirm_lines", "labelKey": "indicatorIde.editor.showConfirmationLevels", "type": "bool"},
                {"key": "sfp_labels", "labelKey": "indicatorIde.editor.showSfpLabels", "type": "bool"},
                {"key": "bull_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
                {"key": "bear_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
                {"key": "validation", "labelKey": "indicatorIde.editor.validationMode", "type": "string"},
                {
                    "key": "percent",
                    "labelKey": "indicatorIde.editor.sweepPenetration",
                    "type": "number",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "breaks_and_retests",
            "Breaks and Retests",
            "Break/Retest",
            "band",
            {
                "lookback": 20,
                "ret_since": 2,
                "ret_valid": 2,
                "breakouts": True,
                "retests": True,
                "support_color": "#FF0000",
                "resistance_color": "#089981",
            },
            [
                {
                    "key": "lookback",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "ret_since",
                    "labelKey": "indicatorIde.editor.retestStartBars",
                    "type": "number",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "ret_valid",
                    "labelKey": "indicatorIde.editor.retestWindow",
                    "type": "number",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                },
                {"key": "breakouts", "labelKey": "indicatorIde.editor.showBreakouts", "type": "bool"},
                {"key": "retests", "labelKey": "indicatorIde.editor.showRetests", "type": "bool"},
                {"key": "support_color", "labelKey": "indicatorIde.editor.supportColor", "type": "color"},
                {"key": "resistance_color", "labelKey": "indicatorIde.editor.resistanceColor", "type": "color"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "false_breakout",
            "False Breakout",
            "False Breakout",
            "band",
            {"prd": 20, "minperiod": 5, "maxperiod": 5, "ma_type": "None", "length": 10, "aggressive": False},
            [
                {
                    "key": "prd",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "minperiod",
                    "labelKey": "indicatorIde.editor.breakoutGap",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "maxperiod",
                    "labelKey": "indicatorIde.editor.signalValidity",
                    "type": "number",
                    "min": 0,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "ma_type",
                    "labelKey": "indicatorIde.editor.smoothingMethod",
                    "type": "string",
                    "options": ["None", "WMA", "HMA"],
                },
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {"key": "aggressive", "labelKey": "indicatorIde.editor.aggressiveSource", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "multi_kernel_regression",
            "Multi Kernel Regression",
            "Kernel Regression",
            "band",
            {
                "repaint": True,
                "kernel": "Laplace",
                "bandwidth": 14,
                "source": "close",
                "deviations": 2.0,
                "enable": False,
                "bullish_color": "#54C294",
                "bearish_color": "#EB3939",
                "confirm_bars": 10,
            },
            [
                {"key": "repaint", "labelKey": "indicatorIde.editor.compatibilityRepaint", "type": "bool"},
                {
                    "key": "kernel",
                    "labelKey": "indicatorIde.editor.kernelType",
                    "type": "string",
                    "options": [
                        "Triangular",
                        "Gaussian",
                        "Epanechnikov",
                        "Logistic",
                        "Log Logistic",
                        "Cosine",
                        "Sinc",
                        "Laplace",
                        "Quartic",
                        "Parabolic",
                        "Exponential",
                        "Silverman",
                        "Cauchy",
                        "Tent",
                        "Wave",
                        "Power",
                        "Morters",
                    ],
                },
                {
                    "key": "bandwidth",
                    "labelKey": "indicatorIde.editor.bandwidth",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "deviations",
                    "labelKey": "indicatorIde.editor.deviation",
                    "type": "number",
                    "min": 0,
                    "max": 10,
                    "step": 0.25,
                },
                {"key": "enable", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
                {"key": "bullish_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
                {"key": "bearish_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
                {
                    "key": "confirm_bars",
                    "labelKey": "indicatorIde.editor.confirmationBars",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "smart_money_breakouts",
            "Smart Money Breakouts",
            "SM Breakouts",
            "band",
            {
                "length": 20,
                "candle_type": "Wicks",
                "rr_ratio": 1.1,
                "sl_type": "Close",
                "show_sl": False,
                "line_style": "Dashed",
                "pivot_high_color": "#028545",
                "pivot_low_color": "#F60707",
                "tp_color": "#148D9A",
                "sl_color": "#F60707",
            },
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "candle_type",
                    "labelKey": "indicatorIde.editor.breakoutSource",
                    "type": "string",
                    "options": ["Wicks", "Body"],
                },
                {
                    "key": "rr_ratio",
                    "labelKey": "indicatorIde.editor.rewardRiskRatio",
                    "type": "number",
                    "min": 0.1,
                    "max": 20,
                    "step": 0.1,
                },
                {
                    "key": "sl_type",
                    "labelKey": "indicatorIde.editor.stopTrigger",
                    "type": "string",
                    "options": ["Close", "High/Low"],
                },
                {"key": "show_sl", "labelKey": "indicatorIde.editor.showStopLine", "type": "bool"},
                {
                    "key": "line_style",
                    "labelKey": "indicatorIde.editor.lineStyle",
                    "type": "string",
                    "options": ["Solid", "Dashed", "Dotted"],
                },
                {"key": "pivot_high_color", "labelKey": "indicatorIde.editor.pivotHighColor", "type": "color"},
                {"key": "pivot_low_color", "labelKey": "indicatorIde.editor.pivotLowColor", "type": "color"},
                {"key": "tp_color", "labelKey": "indicatorIde.editor.takeProfitColor", "type": "color"},
                {"key": "sl_color", "labelKey": "indicatorIde.editor.stopLossColor", "type": "color"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "swing_highs_lows_candle_patterns",
            "Swing Highs/Lows & Candle Patterns",
            "Swing Patterns",
            "band",
            {"length": 21},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "trendlines_with_breaks",
            "Trendlines with Breaks",
            "Trendline Breaks",
            "band",
            {"length": 14, "mult": 1.0, "calc_method": "Atr", "unique_signal": False},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "mult",
                    "labelKey": "indicatorIde.editor.slopeMultiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                },
                {
                    "key": "calc_method",
                    "labelKey": "indicatorIde.editor.slopeMethod",
                    "type": "string",
                    "options": ["Atr", "Stdev", "Linreg"],
                },
                {"key": "unique_signal", "labelKey": "indicatorIde.editor.uniqueBreakouts", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "rsi_divergence_indicator",
            "RSI Divergence Indicator",
            "RSI Divergence",
            "line",
            {
                "length": 9,
                "source": "close",
                "pivot_left": 1,
                "pivot_right": 3,
                "range_lower": 5,
                "range_upper": 60,
                "plot_bull": True,
                "plot_hidden_bull": True,
                "plot_bear": True,
                "plot_hidden_bear": False,
            },
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "open", "high", "low"],
                },
                {
                    "key": "pivot_left",
                    "labelKey": "indicatorIde.editor.pivotLeft",
                    "type": "number",
                    "min": 1,
                    "max": 20,
                    "step": 1,
                },
                {
                    "key": "pivot_right",
                    "labelKey": "indicatorIde.editor.pivotRight",
                    "type": "number",
                    "min": 1,
                    "max": 20,
                    "step": 1,
                },
                {
                    "key": "range_lower",
                    "labelKey": "indicatorIde.editor.rangeLower",
                    "type": "number",
                    "min": 1,
                    "max": 500,
                    "step": 1,
                },
                {
                    "key": "range_upper",
                    "labelKey": "indicatorIde.editor.rangeUpper",
                    "type": "number",
                    "min": 2,
                    "max": 1000,
                    "step": 1,
                },
                {"key": "plot_bull", "labelKey": "indicatorIde.editor.showBullish", "type": "bool"},
                {"key": "plot_hidden_bull", "labelKey": "indicatorIde.editor.showHiddenBullish", "type": "bool"},
                {"key": "plot_bear", "labelKey": "indicatorIde.editor.showBearish", "type": "bool"},
                {"key": "plot_hidden_bear", "labelKey": "indicatorIde.editor.showHiddenBearish", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "two_b_reversal_pattern",
            "2B Reversal Pattern (Expo)",
            "2B Reversal",
            "band",
            {
                "prd": 20,
                "max_break": 10,
                "min_break": 3,
                "setup_src": "close",
                "confirm_src": "close",
                "cancel_on_invalid_cross": True,
                "allow_multiple": False,
                "signal_mode": "Custom",
                "bUp": "#6ce5a0",
                "bDn": "#f23645",
                "pCol": "#00FFFF",
            },
            [
                {
                    "key": "prd",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "max_break",
                    "labelKey": "indicatorIde.editor.confirmationWindow",
                    "type": "number",
                    "min": 0,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "min_break",
                    "labelKey": "indicatorIde.editor.minimumBreakBars",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "setup_src",
                    "labelKey": "indicatorIde.editor.setupSource",
                    "type": "string",
                    "options": ["close", "wick"],
                },
                {
                    "key": "confirm_src",
                    "labelKey": "indicatorIde.editor.confirmationSource",
                    "type": "string",
                    "options": ["close", "wick"],
                },
                {
                    "key": "cancel_on_invalid_cross",
                    "labelKey": "indicatorIde.editor.cancelInvalidSetup",
                    "type": "bool",
                },
                {"key": "allow_multiple", "labelKey": "indicatorIde.editor.allowMultipleSetups", "type": "bool"},
                {
                    "key": "signal_mode",
                    "labelKey": "indicatorIde.editor.signalMode",
                    "type": "string",
                    "options": ["Custom", "Original", "Relaxed", "Aggressive"],
                },
                {"key": "bUp", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
                {"key": "bDn", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
                {"key": "pCol", "labelKey": "indicatorIde.editor.pivotColor", "type": "color"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "alphatrend_screener",
            "AlphaTrend Screener",
            "AlphaTrend",
            "band",
            {"coeff": 1.0, "period": 14, "use_mfi": True, "show_signal": True},
            [
                {
                    "key": "coeff",
                    "labelKey": "indicatorIde.editor.atrCoefficient",
                    "type": "number",
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                },
                {
                    "key": "period",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {"key": "use_mfi", "labelKey": "indicatorIde.editor.useMfi", "type": "bool"},
                {"key": "show_signal", "labelKey": "indicatorIde.editor.showSignal", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "macd_bollinger_bands",
            "MACD Bollinger Bands",
            "MACD BB",
            "line",
            {
                "fast_length": 12,
                "slow_length": 26,
                "signal_length": 9,
                "band_length": 20,
                "band_multiplier": 2.0,
                "source": "close",
                "show_bands": True,
                "show_signals": True,
            },
            [
                {
                    "key": "fast_length",
                    "labelKey": "indicatorIde.editor.fastPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "slow_length",
                    "labelKey": "indicatorIde.editor.slowPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "signal_length",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "band_length",
                    "labelKey": "indicatorIde.editor.bollingerPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "band_multiplier",
                    "labelKey": "indicatorIde.editor.deviation",
                    "type": "number",
                    "min": 0.5,
                    "max": 4.0,
                    "step": 0.1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {"key": "show_bands", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
                {"key": "show_signals", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "rmi_trend_sniper",
            "RMI Trend Sniper",
            "RMI Sniper",
            "band",
            {"length": 14, "pmom": 66.0, "nmom": 30.0, "filleshow": True},
            [
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "pmom",
                    "labelKey": "indicatorIde.editor.positiveMomentumThreshold",
                    "type": "number",
                    "min": 50,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "nmom",
                    "labelKey": "indicatorIde.editor.negativeMomentumThreshold",
                    "type": "number",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                },
                {"key": "filleshow", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "smart_money_breakout_signals",
            "Smart Money Breakout Signals",
            "SM BOS",
            "band",
            {"swing_length": 5, "volume_length": 20, "volume_multiplier": 1.0, "use_volume": True, "show_levels": True},
            [
                {
                    "key": "swing_length",
                    "labelKey": "indicatorIde.editor.swingPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "volume_length",
                    "labelKey": "indicatorIde.editor.volumePeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "volume_multiplier",
                    "labelKey": "indicatorIde.editor.volatilityMultiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                },
                {"key": "use_volume", "labelKey": "indicatorIde.editor.useVolumeFilter", "type": "bool"},
                {"key": "show_levels", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "auto_chart_patterns",
            "Auto Chart Patterns",
            "Chart Patterns",
            "band",
            {
                "source": "close",
                "threshold": 0.01,
                "min_pivots": 4,
                "max_pivots": 6,
                "error_ratio": 0.02,
                "flat_ratio": 0.2,
                "conv_eps": 0.05,
                "allow_channels": True,
                "allow_wedges": True,
                "allow_triangles": True,
                "max_patterns": 6,
                "avoid_overlap": True,
            },
            [
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.patternSource",
                    "type": "string",
                    "options": ["close", "hl2"],
                },
                {
                    "key": "threshold",
                    "labelKey": "indicatorIde.editor.patternThreshold",
                    "type": "number",
                    "min": 0.001,
                    "max": 0.2,
                    "step": 0.001,
                },
                {
                    "key": "min_pivots",
                    "labelKey": "indicatorIde.editor.minimumPivots",
                    "type": "number",
                    "min": 4,
                    "max": 6,
                    "step": 1,
                },
                {
                    "key": "max_pivots",
                    "labelKey": "indicatorIde.editor.maximumPivots",
                    "type": "number",
                    "min": 4,
                    "max": 6,
                    "step": 1,
                },
                {
                    "key": "error_ratio",
                    "labelKey": "indicatorIde.editor.fitErrorTolerance",
                    "type": "number",
                    "min": 0.001,
                    "max": 0.2,
                    "step": 0.001,
                },
                {
                    "key": "flat_ratio",
                    "labelKey": "indicatorIde.editor.flatSlopeRatio",
                    "type": "number",
                    "min": 0.01,
                    "max": 1.0,
                    "step": 0.01,
                },
                {
                    "key": "conv_eps",
                    "labelKey": "indicatorIde.editor.convergenceTolerance",
                    "type": "number",
                    "min": 0.001,
                    "max": 0.5,
                    "step": 0.001,
                },
                {"key": "allow_channels", "labelKey": "indicatorIde.editor.detectChannels", "type": "bool"},
                {"key": "allow_wedges", "labelKey": "indicatorIde.editor.detectWedges", "type": "bool"},
                {"key": "allow_triangles", "labelKey": "indicatorIde.editor.detectTriangles", "type": "bool"},
                {
                    "key": "max_patterns",
                    "labelKey": "indicatorIde.editor.patternHistory",
                    "type": "number",
                    "min": 4,
                    "max": 6,
                    "step": 1,
                },
                {"key": "avoid_overlap", "labelKey": "indicatorIde.editor.avoidPatternOverlap", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "divergence_many_indicators",
            "Divergence for Many Indicators v4",
            "Multi Divergence",
            "line",
            {
                "pivot_period": 5,
                "source": "Close",
                "div_type": "Regular",
                "max_bars": 100,
                "show_names": "Full",
                "show_number": True,
                "calc_macd": True,
                "calc_hist": True,
                "calc_rsi": True,
                "calc_stoch": True,
                "calc_cci": True,
                "calc_mom": True,
                "calc_obv": True,
                "calc_vwmacd": True,
                "calc_cmf": True,
                "calc_mfi": True,
                "calc_ext": False,
            },
            [
                {
                    "key": "pivot_period",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 20,
                    "step": 1,
                },
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.divergenceSource",
                    "type": "string",
                    "options": ["Close", "High/Low"],
                },
                {
                    "key": "div_type",
                    "labelKey": "indicatorIde.editor.divergenceType",
                    "type": "string",
                    "options": ["Regular", "Hidden", "Both"],
                },
                {
                    "key": "max_bars",
                    "labelKey": "indicatorIde.editor.maximumPivotDistance",
                    "type": "number",
                    "min": 10,
                    "max": 500,
                    "step": 10,
                },
                {
                    "key": "show_names",
                    "labelKey": "indicatorIde.editor.signalDetail",
                    "type": "string",
                    "options": ["Full", "Short", "None"],
                },
                {"key": "show_number", "labelKey": "indicatorIde.editor.showConfirmationCount", "type": "bool"},
                {"key": "calc_macd", "labelKey": "indicatorIde.editor.includeMacd", "type": "bool"},
                {"key": "calc_hist", "labelKey": "indicatorIde.editor.includeMacdHistogram", "type": "bool"},
                {"key": "calc_rsi", "labelKey": "indicatorIde.editor.includeRsi", "type": "bool"},
                {"key": "calc_stoch", "labelKey": "indicatorIde.editor.includeStochastic", "type": "bool"},
                {"key": "calc_cci", "labelKey": "indicatorIde.editor.includeCci", "type": "bool"},
                {"key": "calc_mom", "labelKey": "indicatorIde.editor.includeMomentum", "type": "bool"},
                {"key": "calc_obv", "labelKey": "indicatorIde.editor.includeObv", "type": "bool"},
                {"key": "calc_vwmacd", "labelKey": "indicatorIde.editor.includeVolumeMacd", "type": "bool"},
                {"key": "calc_cmf", "labelKey": "indicatorIde.editor.includeCmf", "type": "bool"},
                {"key": "calc_mfi", "labelKey": "indicatorIde.editor.includeMfi", "type": "bool"},
                {"key": "calc_ext", "labelKey": "indicatorIde.editor.includeExternalMomentum", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "trading_abc",
            "Trading ABC",
            "Trading ABC",
            "band",
            {
                "prd": 8,
                "fiboup": 0.618,
                "fibodn": 0.382,
                "errorrate": 5.0,
                "src_ma": "close",
                "malen1": 50,
                "malen2": 100,
                "malen3": 150,
                "malen4": 200,
                "malen5": 20,
                "malen6": 40,
                "showabc": True,
                "keepabc": True,
                "showcloud": True,
                "showzigzag": True,
            },
            [
                {
                    "key": "prd",
                    "labelKey": "indicatorIde.editor.pivotPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 40,
                    "step": 1,
                },
                {
                    "key": "fiboup",
                    "labelKey": "indicatorIde.editor.upperRetracement",
                    "type": "number",
                    "min": 0.1,
                    "max": 1.5,
                    "step": 0.001,
                },
                {
                    "key": "fibodn",
                    "labelKey": "indicatorIde.editor.lowerRetracement",
                    "type": "number",
                    "min": 0.1,
                    "max": 1.5,
                    "step": 0.001,
                },
                {
                    "key": "errorrate",
                    "labelKey": "indicatorIde.editor.ratioTolerance",
                    "type": "number",
                    "min": 0,
                    "max": 25,
                    "step": 0.5,
                },
                {
                    "key": "src_ma",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "malen1",
                    "labelKey": "indicatorIde.editor.smaLength1",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "malen2",
                    "labelKey": "indicatorIde.editor.smaLength2",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "malen3",
                    "labelKey": "indicatorIde.editor.smaLength3",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "malen4",
                    "labelKey": "indicatorIde.editor.smaLength4",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "malen5",
                    "labelKey": "indicatorIde.editor.emaLength1",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {
                    "key": "malen6",
                    "labelKey": "indicatorIde.editor.emaLength2",
                    "type": "number",
                    "min": 2,
                    "max": 300,
                    "step": 1,
                },
                {"key": "showabc", "labelKey": "indicatorIde.editor.showAbcLine", "type": "bool"},
                {"key": "keepabc", "labelKey": "indicatorIde.editor.keepConfirmedAbc", "type": "bool"},
                {"key": "showcloud", "labelKey": "indicatorIde.editor.useTrendFilter", "type": "bool"},
                {"key": "showzigzag", "labelKey": "indicatorIde.editor.showZigzag", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "pmax_on_rsi_t3",
            "PMax on RSI w T3",
            "PMax RSI T3",
            "line",
            {
                "source": "hl2",
                "multiplier": 1.0,
                "t3_length": 8,
                "t3_factor": 0.7,
                "atr_length": 10,
                "rsi_length": 14,
                "show_rsi": True,
                "show_support": True,
                "show_signals": True,
                "highlighting": True,
            },
            [
                {
                    "key": "source",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["hl2", "hlc3", "close", "open", "high", "low"],
                },
                {
                    "key": "multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                },
                {
                    "key": "t3_length",
                    "labelKey": "indicatorIde.editor.t3Period",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "t3_factor",
                    "labelKey": "indicatorIde.editor.smoothingFactor",
                    "type": "number",
                    "min": 0,
                    "max": 1,
                    "step": 0.05,
                },
                {
                    "key": "atr_length",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "rsi_length",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "show_rsi", "labelKey": "indicatorIde.editor.showRsi", "type": "bool"},
                {"key": "show_support", "labelKey": "indicatorIde.editor.showSupport", "type": "bool"},
                {"key": "show_signals", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
                {"key": "highlighting", "labelKey": "indicatorIde.editor.highlightTrend", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "volume_weighted_macd",
            "Volume Weighted MACD",
            "VW-MACD",
            "line",
            {"fast_length": 12, "slow_length": 26, "signal_length": 9, "histogram": True},
            [
                {
                    "key": "fast_length",
                    "labelKey": "indicatorIde.editor.fastPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "slow_length",
                    "labelKey": "indicatorIde.editor.slowPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_length",
                    "labelKey": "indicatorIde.editor.signalPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "histogram", "labelKey": "indicatorIde.editor.showHistogram", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "itg_scalper",
            "ITG Scalper",
            "ITG Scalper",
            "band",
            {"fast_length": 5, "slow_length": 13, "atr_length": 14, "atr_multiplier": 1.5, "show_bands": True},
            [
                {
                    "key": "fast_length",
                    "labelKey": "indicatorIde.editor.fastPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "slow_length",
                    "labelKey": "indicatorIde.editor.slowPeriod",
                    "type": "number",
                    "min": 3,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "atr_length",
                    "labelKey": "indicatorIde.editor.atrPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "atr_multiplier",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                },
                {"key": "show_bands", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "machine_learning_rsi",
            "Machine Learning RSI",
            "ML RSI",
            "line",
            {
                "rsi_length": 14,
                "use_smoothing": True,
                "smoothing_length": 3,
                "ma_type": "ALMA",
                "alma_sigma": 4.0,
                "use_knn": True,
                "knn_neighbors": 5,
                "knn_lookback": 100,
                "knn_weight": 0.4,
                "feature_count": 3,
                "use_filter": True,
                "filter_method": "Kalman",
                "filter_strength": 0.3,
                "src": "close",
                "overbought": 70,
                "oversold": 30,
                "color_scheme": "Classic",
                "neon_effect": True,
                "color_mode": "Trend Following",
                "show_table": True,
                "table_position": "top-left",
            },
            [
                {
                    "key": "rsi_length",
                    "labelKey": "indicatorIde.editor.rsiPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "use_smoothing", "labelKey": "indicatorIde.editor.useSmoothing", "type": "bool"},
                {
                    "key": "smoothing_length",
                    "labelKey": "indicatorIde.editor.smoothing",
                    "type": "number",
                    "min": 1,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "ma_type",
                    "labelKey": "indicatorIde.editor.smoothingMethod",
                    "type": "string",
                    "options": ["SMA", "EMA", "DEMA", "TEMA", "WMA", "VWMA", "SMMA", "HMA", "LSMA", "ALMA"],
                },
                {
                    "key": "alma_sigma",
                    "labelKey": "indicatorIde.editor.almaSigma",
                    "type": "number",
                    "min": 1,
                    "max": 10,
                    "step": 0.5,
                },
                {"key": "use_knn", "labelKey": "indicatorIde.editor.enableKnn", "type": "bool"},
                {
                    "key": "knn_neighbors",
                    "labelKey": "indicatorIde.editor.knnNeighbors",
                    "type": "number",
                    "min": 1,
                    "max": 32,
                    "step": 1,
                },
                {
                    "key": "knn_lookback",
                    "labelKey": "indicatorIde.editor.knnLookback",
                    "type": "number",
                    "min": 20,
                    "max": 500,
                    "step": 10,
                },
                {
                    "key": "knn_weight",
                    "labelKey": "indicatorIde.editor.knnWeight",
                    "type": "number",
                    "min": 0,
                    "max": 1,
                    "step": 0.05,
                },
                {
                    "key": "feature_count",
                    "labelKey": "indicatorIde.editor.featureCount",
                    "type": "number",
                    "min": 1,
                    "max": 5,
                    "step": 1,
                },
                {"key": "use_filter", "labelKey": "indicatorIde.editor.applyRsiFilter", "type": "bool"},
                {
                    "key": "filter_method",
                    "labelKey": "indicatorIde.editor.filterMethod",
                    "type": "string",
                    "options": ["Kalman", "DoubleEMA", "ALMA"],
                },
                {
                    "key": "filter_strength",
                    "labelKey": "indicatorIde.editor.filterStrength",
                    "type": "number",
                    "min": 0.05,
                    "max": 1,
                    "step": 0.05,
                },
                {
                    "key": "src",
                    "labelKey": "indicatorIde.editor.priceSource",
                    "type": "string",
                    "options": ["close", "hl2", "hlc3", "ohlc4"],
                },
                {
                    "key": "overbought",
                    "labelKey": "indicatorIde.editor.overbought",
                    "type": "number",
                    "min": 50,
                    "max": 95,
                    "step": 1,
                },
                {
                    "key": "oversold",
                    "labelKey": "indicatorIde.editor.oversold",
                    "type": "number",
                    "min": 5,
                    "max": 50,
                    "step": 1,
                },
                {
                    "key": "color_scheme",
                    "labelKey": "indicatorIde.editor.colorScheme",
                    "type": "string",
                    "options": ["Classic", "Deuteranopia", "Protanopia", "Tritanopia", "Monochrome"],
                },
                {"key": "neon_effect", "labelKey": "indicatorIde.editor.neonEffect", "type": "bool"},
                {
                    "key": "color_mode",
                    "labelKey": "indicatorIde.editor.colorMode",
                    "type": "string",
                    "options": ["None", "Trend Following", "Impulse"],
                },
                {"key": "show_table", "labelKey": "indicatorIde.editor.compatibilityTable", "type": "bool"},
                {
                    "key": "table_position",
                    "labelKey": "indicatorIde.editor.compatibilityTablePosition",
                    "type": "string",
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "ghost_tangent_crossings",
            "Ghost Tangent Crossings",
            "Ghost Tangents",
            "band",
            {
                "pivot_type": "Wick",
                "pivot_forward": 25,
                "show_elliptical_zig": True,
                "show_ghosts": True,
                "show_break": True,
                "max_zig": 0,
                "equipoint_style": "Directional",
                "extend_line": False,
                "up_color": "#1bcf66",
                "down_color": "#ee2d2d",
                "ghost_up_color": "#1bcf663a",
                "ghost_down_color": "#ee2d2d3a",
                "text_color": "#EEEEEE",
            },
            [
                {
                    "key": "pivot_type",
                    "labelKey": "indicatorIde.editor.pivotSource",
                    "type": "string",
                    "options": ["Wick", "Body"],
                },
                {
                    "key": "pivot_forward",
                    "labelKey": "indicatorIde.editor.pivotRight",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {"key": "show_elliptical_zig", "labelKey": "indicatorIde.editor.showConfirmedSwings", "type": "bool"},
                {"key": "show_ghosts", "labelKey": "indicatorIde.editor.showProvisionalSwings", "type": "bool"},
                {"key": "show_break", "labelKey": "indicatorIde.editor.showTangentCrossings", "type": "bool"},
                {
                    "key": "max_zig",
                    "labelKey": "indicatorIde.editor.maximumSwings",
                    "type": "number",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "equipoint_style",
                    "labelKey": "indicatorIde.editor.equipointStyle",
                    "type": "string",
                    "options": ["Directional", "Horizontal", "None"],
                },
                {"key": "extend_line", "labelKey": "indicatorIde.editor.extendProjection", "type": "bool"},
                {"key": "up_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "string"},
                {"key": "down_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "string"},
                {"key": "ghost_up_color", "labelKey": "indicatorIde.editor.ghostBullishColor", "type": "string"},
                {"key": "ghost_down_color", "labelKey": "indicatorIde.editor.ghostBearishColor", "type": "string"},
                {"key": "text_color", "labelKey": "indicatorIde.editor.markerTextColor", "type": "string"},
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "volume_supertrend_ai",
            "Volume SuperTrend AI",
            "Volume ST AI",
            "band",
            {
                "k": 3,
                "n_data": 10,
                "knn_price_len": 20,
                "knn_st_len": 100,
                "ai_signals": True,
                "bullish_col": "#00FF00",
                "bearish_col": "#FF0000",
                "length": 10,
                "factor": 3.0,
                "ma_src": "WMA",
                "up_col": "#00FF00",
                "dn_col": "#FF0000",
                "ne_col": "#0000FF",
                "show_cloud": True,
                "cloud_bull": "#00FF00",
                "cloud_bear": "#FF0000",
                "cloud_transp": 78,
                "cloud_ref_len": 10,
                "cloud_line_smooth": 2,
                "cloud_layers": 3,
            },
            [
                {
                    "key": "k",
                    "labelKey": "indicatorIde.editor.knnNeighbors",
                    "type": "number",
                    "min": 1,
                    "max": 32,
                    "step": 1,
                },
                {
                    "key": "n_data",
                    "labelKey": "indicatorIde.editor.knnHistoryWindow",
                    "type": "number",
                    "min": 1,
                    "max": 500,
                    "step": 1,
                },
                {
                    "key": "knn_price_len",
                    "labelKey": "indicatorIde.editor.priceWmaPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "knn_st_len",
                    "labelKey": "indicatorIde.editor.supertrendWmaPeriod",
                    "type": "number",
                    "min": 2,
                    "max": 500,
                    "step": 1,
                },
                {"key": "ai_signals", "labelKey": "indicatorIde.editor.showAiSignals", "type": "bool"},
                {"key": "bullish_col", "labelKey": "indicatorIde.editor.bullishSignalColor", "type": "color"},
                {"key": "bearish_col", "labelKey": "indicatorIde.editor.bearishSignalColor", "type": "color"},
                {
                    "key": "length",
                    "labelKey": "indicatorIde.editor.period",
                    "type": "number",
                    "min": 2,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "factor",
                    "labelKey": "indicatorIde.editor.multiplier",
                    "type": "number",
                    "min": 0.1,
                    "max": 10,
                    "step": 0.1,
                },
                {
                    "key": "ma_src",
                    "labelKey": "indicatorIde.editor.movingAverageType",
                    "type": "string",
                    "options": ["SMA", "EMA", "WMA", "RMA", "VWMA"],
                },
                {"key": "up_col", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
                {"key": "dn_col", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
                {"key": "ne_col", "labelKey": "indicatorIde.editor.neutralColor", "type": "color"},
                {"key": "show_cloud", "labelKey": "indicatorIde.editor.showCloud", "type": "bool"},
                {"key": "cloud_bull", "labelKey": "indicatorIde.editor.bullishCloudColor", "type": "color"},
                {"key": "cloud_bear", "labelKey": "indicatorIde.editor.bearishCloudColor", "type": "color"},
                {
                    "key": "cloud_transp",
                    "labelKey": "indicatorIde.editor.cloudTransparency",
                    "type": "number",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "cloud_ref_len",
                    "labelKey": "indicatorIde.editor.cloudReferencePeriod",
                    "type": "number",
                    "min": 1,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "cloud_line_smooth",
                    "labelKey": "indicatorIde.editor.cloudSmoothing",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "cloud_layers",
                    "labelKey": "indicatorIde.editor.cloudLayers",
                    "type": "number",
                    "min": 1,
                    "max": 3,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition(
            "chip_distribution",
            "Chip Distribution",
            "Chip",
            "profile",
            {"lookback": 120, "rows": 48, "value_area_percent": 70},
            [
                {
                    "key": "lookback",
                    "labelKey": "indicatorIde.editor.lookback",
                    "type": "number",
                    "min": 10,
                    "max": 5000,
                    "step": 1,
                },
                {
                    "key": "rows",
                    "labelKey": "indicatorIde.chipDistribution.priceLevels",
                    "type": "number",
                    "min": 8,
                    "max": 120,
                    "step": 1,
                },
                {
                    "key": "value_area_percent",
                    "labelKey": "indicatorIde.chipDistribution.valueAreaPercent",
                    "type": "number",
                    "min": 50,
                    "max": 99,
                    "step": 1,
                },
            ],
            _chip_distribution,
            True,
            alert_mode="none",
        ),
        ChartIndicatorDefinition(
            "z_score", "Z-Score", "Z-Score", "line", {"period": 20}, _period_schema("period", maximum=300), None
        ),
        ChartIndicatorDefinition(
            "pvo",
            "Percentage Volume Oscillator",
            "PVO",
            "line",
            {"short_period": 12, "long_period": 26, "signal_period": 9},
            [
                {
                    "key": "short_period",
                    "labelKey": "indicatorIde.editor.fastLine",
                    "type": "number",
                    "min": 2,
                    "max": 100,
                    "step": 1,
                },
                {
                    "key": "long_period",
                    "labelKey": "indicatorIde.editor.slowLine",
                    "type": "number",
                    "min": 3,
                    "max": 200,
                    "step": 1,
                },
                {
                    "key": "signal_period",
                    "labelKey": "indicatorIde.editor.signalLine",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": 1,
                },
            ],
            None,
        ),
        ChartIndicatorDefinition("nvi", "Negative Volume Index", "NVI", "line", {}, [], None),
    ]
    return {item.indicator_id: item for item in defs}


_DEFINITIONS = _make_definitions()


def get_chart_indicator_definition(indicator_id: str) -> ChartIndicatorDefinition | None:
    """Return a built-in definition by its stable catalog identifier."""
    return _DEFINITIONS.get(str(indicator_id or "").strip())


def is_chart_indicator_computable(indicator_id: str) -> bool:
    """Return whether the backend has an implementation for this indicator."""
    definition = get_chart_indicator_definition(indicator_id)
    return bool(definition and (definition.compute is not None or get_indicator_compute(definition.indicator_id) is not None))


def list_chart_indicators() -> list[dict[str, Any]]:
    return [definition.metadata() for definition in _DEFINITIONS.values()]


def compute_chart_indicators(frame: pd.DataFrame, requests: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    results = []
    for item in requests:
        indicator_id = str(item.get("id") or "").strip()
        request_key = item.get("requestKey")
        definition = _DEFINITIONS.get(indicator_id)
        if definition is None:
            results.append(
                {"id": indicator_id, "requestKey": request_key, "success": False, "error": "indicator.notFound"}
            )
            continue
        raw_params = item.get("params") if isinstance(item.get("params"), Mapping) else {}
        params = {**definition.default_params, **raw_params}
        try:
            params = _normalize_indicator_params(definition, params)
            compute = definition.compute
            compute = compute or get_indicator_compute(indicator_id)
            if compute is None:
                raise RuntimeError("indicator implementation is missing")
            result = _normalize_indicator_result(definition, frame, compute(frame, params))
            result.update({"id": indicator_id, "requestKey": request_key, "success": True, "params": params})
            results.append(result)
        except ValueError as exc:
            results.append({"id": indicator_id, "requestKey": request_key, "success": False, "error": str(exc)})
        except Exception:
            results.append(
                {"id": indicator_id, "requestKey": request_key, "success": False, "error": "indicator.computeFailed"}
            )
    return results
