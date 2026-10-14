"""Server-side chart indicator catalog and aligned series calculations.

The chart owns layout and rendering; this module owns indicator definitions and
numeric calculations. Every returned series is aligned one-to-one with the
submitted OHLCV bars and uses ``None`` for warm-up or invalid values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from importlib import resources
import re
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd


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
        }
        if self.single_instance:
            metadata["singleInstance"] = True
        return metadata


# Fixed mapping to reviewed, file-backed indicator implementations. Request
# data can select parameters, but never a module or filesystem path.
_SOURCE_FILES = {
    "alpha_trend": "alpha_trend.py",
    "optimized_trend_tracker": "optimized_trend_tracker.py",
    "std_filtered_gaussian": "std_filtered_n_pole_gaussian_filter.py",
    "adaptive_trend_filter": "adaptive_trend_filter.py",
    "vegas_supertrend": "multi_step_vegas_supertrend.py",
    "dsav": "dsav_dynamic_swing_vwap.py",
    "lowess": "lowess_locally_weighted_scatterplot_smoothing.py",
    "price_radio": "john_ehlers_price_radio.py",
    "adaptive_trend_trail": "adaptive_trend_trail.py",
    "spma_trend_nal": "spma_trend_nal.py",
    "powertrend_volume_range_filter": "powertrend_volume_range_filter.py",
    "g_channels": "g_channels.py",
    "wavetrend_oscillator": "wavetrend_oscillator.py",
    "nadaraya_watson_envelope": "nadaraya_watson_envelope.py",
    "dynamic_linear_regression_channel": "dynamic_linear_regression_channel.py",
    "ut_bot_alerts": "ut_bot_alerts.py",
    "twin_range_filter": "twin_range_filter.py",
    "pivot_point_supertrend": "pivot_point_supertrend.py",
    "delta_rsi_oscillator": "delta_rsi_oscillator.py",
    "range_filter_signals": "range_filter_signals.py",
    "know_sure_thing": "know_sure_thing.py",
    "macd_leader": "macd_leader.py",
    "envelope_rsi_signals": "envelope_rsi_signals.py",
    "follow_line_indicator": "follow_line_indicator.py",
    "exhaustion_levels": "exhaustion_levels.py",
    "hema_trend_levels": "hema_trend_levels.py",
    "market_structure_oscillator": "market_structure_oscillator.py",
    "adaptive_supertrend": "adaptive_supertrend.py",
    "elder_impulse_system": "elder_impulse_system.py",
    "swing_failure_pattern": "swing_failure_pattern.py",
    "breaks_and_retests": "breaks_and_retests.py",
    "false_breakout": "false_breakout.py",
    "multi_kernel_regression": "multi_kernel_regression.py",
    "smart_money_breakouts": "smart_money_breakouts.py",
    "swing_highs_lows_candle_patterns": "swing_highs_lows_candle_patterns.py",
    "trendlines_with_breaks": "trendlines_with_breaks.py",
    "rsi_divergence_indicator": "rsi_divergence_indicator.py",
    "two_b_reversal_pattern": "two_b_reversal_pattern.py",
    "alphatrend_screener": "alphatrend_screener.py",
    "macd_bollinger_bands": "macd_bollinger_bands.py",
    "rmi_trend_sniper": "rmi_trend_sniper.py",
    "smart_money_breakout_signals": "smart_money_breakout_signals.py",
    "auto_chart_patterns": "auto_chart_patterns.py",
    "divergence_many_indicators": "divergence_many_indicators.py",
    "trading_abc": "trading_abc.py",
    "pmax_on_rsi_t3": "pmax_on_rsi_t3.py",
    "volume_weighted_macd": "volume_weighted_macd.py",
    "itg_scalper": "itg_scalper.py",
    "machine_learning_rsi": "machine_learning_rsi.py",
    "ghost_tangent_crossings": "ghost_tangent_crossings.py",
    "volume_supertrend_ai": "volume_supertrend_ai.py",
    "z_score": "z_score.py",
    "pvo": "percentage_volume_oscillator.py",
    "nvi": "negative_volume_index.py",
}


@lru_cache(maxsize=None)
def _compiled_indicator_source(source_file: str) -> Any:
    source = (
        resources.files("app.services.indicator_library.sources")
        .joinpath(source_file)
        .read_text(encoding="utf-8")
    )
    return compile(source, source_file, "exec")


def _normalize_source_params(definition: ChartIndicatorDefinition, params: Mapping[str, Any]) -> dict[str, Any]:
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


def _compute_indicator_source(
    indicator_id: str,
    definition: ChartIndicatorDefinition,
    frame: pd.DataFrame,
    params: Mapping[str, Any],
) -> dict[str, Any]:
    namespace: dict[str, Any] = {
        "df": frame.copy(),
        "params": dict(params),
        "pd": pd,
        "np": np,
        "output": None,
    }
    exec(_compiled_indicator_source(_SOURCE_FILES[indicator_id]), namespace)
    result = namespace.get("output")
    if not isinstance(result, dict):
        raise ValueError("indicator source returned invalid output")

    plots = []
    for index, raw_plot in enumerate(result.get("plots") or []):
        if not isinstance(raw_plot, Mapping):
            continue
        plot = dict(raw_plot)
        title = str(plot.get("title") or plot.get("name") or f"Plot {index + 1}")
        key = str(plot.get("key") or plot.get("name") or f"plot_{index + 1}")
        plot["name"] = key
        plot["title"] = title
        plot["type"] = plot.get("type") or (
            "histogram" if "histogram" in f"{key} {title}".lower() else "line"
        )
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
    item: dict[str, Any] = {"name": key, "title": title, "type": "bar", "data": _clean(values), "overlay": False, "baseValue": 0}
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


def _sma(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    return _output("SMA", [_line("sma", f"SMA({period})", _close(df).rolling(period, min_periods=period).mean(), overlay=True)])


def _ema_indicator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    return _output("EMA", [_line("ema", f"EMA({period})", _ema(_close(df), period), overlay=True)])


def _bollinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    multiplier = _number(params, "mult", 2.0, minimum=0.1, maximum=10)
    close = _close(df)
    middle = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std(ddof=0)
    return _output("Bollinger Bands", [
        _line("upper", f"Upper({period},{multiplier:g})", middle + multiplier * std, overlay=True),
        _line("middle", f"Middle({period})", middle, overlay=True, color="#8c8c8c"),
        _line("lower", f"Lower({period},{multiplier:g})", middle - multiplier * std, overlay=True),
    ])


def _rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    return _output("RSI", [_line("rsi", f"RSI({period})", _rsi_series(_close(df), period))])


def _macd(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast", 12)
    slow = _integer(params, "slow", 26, minimum=2)
    signal = _integer(params, "signal", 9)
    if fast >= slow:
        raise ValueError("invalid parameter: fast")
    close = _close(df)
    line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(line, signal)
    histogram = line - signal_line
    return _output("MACD", [
        _line("macd", f"MACD({fast},{slow})", line),
        _line("signal", f"SIGNAL({signal})", signal_line, color="#fa8c16"),
        _bar("histogram", "HIST", histogram),
    ])


def _atr_indicator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14)
    return _output("ATR", [_line("atr", f"ATR({period})", _atr(df, period))])


def _cci(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    middle = typical.rolling(period, min_periods=period).mean()
    deviation = typical.rolling(period, min_periods=period).apply(lambda values: np.mean(np.abs(values - np.mean(values))), raw=True)
    return _output("CCI", [_line("cci", f"CCI({period})", (typical - middle) / (0.015 * deviation.replace(0, np.nan)))])


def _williams(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    high, low = _series(df, "high"), _series(df, "low")
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    denominator = (highest - lowest).replace(0, np.nan)
    return _output("Williams %R", [_line("williams", f"W%R({period})", -100 * (highest - _close(df)) / denominator)])


def _mfi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    flow = typical * _series(df, "volume").fillna(0)
    direction = typical.diff()
    positive = flow.where(direction > 0, 0).rolling(period, min_periods=period).sum()
    negative = flow.where(direction < 0, 0).rolling(period, min_periods=period).sum()
    ratio = positive / negative.replace(0, np.nan)
    values = 100 - 100 / (1 + ratio)
    values = values.mask((negative == 0) & (positive > 0), 100).mask((negative == 0) & (positive == 0), 0)
    return _output("MFI", [_line("mfi", f"MFI({period})", values)])


def _adx(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    smooth_tr = _wilder(tr, period)
    smooth_plus = _wilder(plus_dm, period)
    smooth_minus = _wilder(minus_dm, period)
    plus_di = 100 * smooth_plus / smooth_tr.replace(0, np.nan)
    minus_di = 100 * smooth_minus / smooth_tr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = _wilder(dx, period)
    return _output("ADX", [
        _line("adx", f"ADX({period})", adx),
        _line("plus_di", "+DI", plus_di, color="#26a69a"),
        _line("minus_di", "-DI", minus_di, color="#ef5350"),
    ])


def _aroon(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 25, minimum=2, maximum=200)
    high, low = _series(df, "high"), _series(df, "low")

    def most_recent_age(values: np.ndarray, find_max: bool) -> float:
        if not np.isfinite(values).all():
            return np.nan
        extreme = np.max(values) if find_max else np.min(values)
        positions = np.flatnonzero(values == extreme)
        return float(len(values) - 1 - positions[-1])

    high_age = high.rolling(period, min_periods=period).apply(
        lambda values: most_recent_age(values, True), raw=True
    )
    low_age = low.rolling(period, min_periods=period).apply(
        lambda values: most_recent_age(values, False), raw=True
    )
    up = 100 * (period - high_age) / period
    down = 100 * (period - low_age) / period
    return _output("Aroon Oscillator", [
        _line("aroon_up", "Aroon Up", up, color="#26a69a"),
        _line("aroon_down", "Aroon Down", down, color="#ef5350"),
        _line("aroon", "Aroon Oscillator", up - down, color="#2962ff"),
    ])


def _stochastic(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14, minimum=3, maximum=200)
    smooth_k = _integer(params, "smooth_k", 3, minimum=1, maximum=50)
    smooth_d = _integer(params, "smooth_d", 3, minimum=1, maximum=50)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    raw_k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    percent_k = raw_k.rolling(smooth_k, min_periods=smooth_k).mean()
    percent_d = percent_k.rolling(smooth_d, min_periods=smooth_d).mean()
    return _output("Stochastic Oscillator", [
        _line("percent_k", f"%K({period},{smooth_k})", percent_k, color="#2962ff"),
        _line("percent_d", f"%D({smooth_d})", percent_d, color="#ff6d00"),
    ])


def _stochastic_rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 14, minimum=2, maximum=100)
    stochastic_period = _integer(params, "stochastic_period", 14, minimum=2, maximum=100)
    k_period = _integer(params, "k_period", 3, minimum=1, maximum=50)
    d_period = _integer(params, "d_period", 3, minimum=1, maximum=50)
    rsi = _rsi_series(_close(df), rsi_period)
    rsi_low = rsi.rolling(stochastic_period, min_periods=stochastic_period).min()
    rsi_high = rsi.rolling(stochastic_period, min_periods=stochastic_period).max()
    rsi_range = rsi_high - rsi_low
    stoch = (rsi - rsi_low) / rsi_range.replace(0, np.nan)
    stoch = stoch.mask((rsi_range == 0) & rsi.notna(), 0.5)
    percent_k = stoch.rolling(k_period, min_periods=k_period).mean() * 100
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return _output("Stochastic RSI", [
        _line("stoch_rsi_k", "%K", percent_k, color="#2962ff"),
        _line("stoch_rsi_d", "%D", percent_d, color="#ff6d00"),
    ])


def _donchian(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    upper = high.rolling(period, min_periods=period).max().shift(1)
    lower = low.rolling(period, min_periods=period).min().shift(1)
    middle = (upper + lower) / 2
    above = (close > upper).fillna(False).to_numpy()
    below = (close < lower).fillna(False).to_numpy()
    previous_above = np.concatenate([[False], above[:-1]])
    previous_below = np.concatenate([[False], below[:-1]])
    buy = [float(low.iloc[index]) if above[index] and not previous_above[index] else None for index in range(len(df))]
    sell = [float(high.iloc[index]) if below[index] and not previous_below[index] else None for index in range(len(df))]
    return {
        **_output("Donchian Channel", [
            _line("donchian_upper", "Donchian Upper", upper, overlay=True, color="#26a69a"),
            _line("donchian_middle", "Donchian Middle", middle, overlay=True, color="#90a4ae"),
            _line("donchian_lower", "Donchian Lower", lower, overlay=True, color="#ef5350"),
        ]),
        "signals": [
            {"type": "buy", "text": "DC+", "data": buy, "color": "#00e676"},
            {"type": "sell", "text": "DC-", "data": sell, "color": "#ff5252"},
        ],
    }


def _keltner(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    atr_period = _integer(params, "atr_period", 10, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 2.0, minimum=0.25, maximum=8.0)
    center = _ema(_close(df), period)
    atr = _atr(df, atr_period)
    return _output("Keltner Channel", [
        _line("keltner_upper", "Keltner Upper", center + multiplier * atr, overlay=True, color="#26a69a"),
        _line("keltner_center", f"EMA({period})", center, overlay=True, color="#2962ff"),
        _line("keltner_lower", "Keltner Lower", center - multiplier * atr, overlay=True, color="#ef5350"),
    ])


def _ichimoku(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    conversion_period = _integer(params, "conversion_period", 9, minimum=2, maximum=100)
    base_period = _integer(params, "base_period", 26, minimum=2, maximum=200)
    span_b_period = _integer(params, "span_b_period", 52, minimum=2, maximum=300)
    high, low = _series(df, "high"), _series(df, "low")

    def midpoint(period: int) -> pd.Series:
        return (high.rolling(period, min_periods=period).max() + low.rolling(period, min_periods=period).min()) / 2

    conversion = midpoint(conversion_period)
    base = midpoint(base_period)
    span_a = (conversion + base) / 2
    span_b = midpoint(span_b_period)
    return _output("Ichimoku Cloud", [
        _line("ichimoku_conversion", "Tenkan-sen", conversion, overlay=True, color="#26a69a"),
        _line("ichimoku_base", "Kijun-sen", base, overlay=True, color="#ef5350"),
        _line("ichimoku_span_a", "Senkou Span A", span_a, overlay=True, color="#66bb6a"),
        _line("ichimoku_span_b", "Senkou Span B", span_b, overlay=True, color="#ab47bc"),
    ])


def _cmf(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    clv = (((close - low) - (high - close)) / (high - low).replace(0, np.nan)).fillna(0)
    denominator = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    values = (clv * volume).rolling(period, min_periods=period).sum() / denominator
    return _output("Chaikin Money Flow", [_line("cmf", f"CMF({period})", values, color="#26a69a")])


def _cmo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    delta = _close(df).diff()
    up = delta.clip(lower=0).rolling(period, min_periods=period).sum()
    down = (-delta.clip(upper=0)).rolling(period, min_periods=period).sum()
    values = 100 * (up - down) / (up + down).replace(0, np.nan)
    return _output("Chande Momentum Oscillator", [_line("cmo", f"CMO({period})", values)])


def _wma(values: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / weights.sum()), raw=True
    )


def _dema(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=300)
    close = _close(df)
    first = _ema(close, period)
    values = 2 * first - _ema(first, period)
    return _output("Double Exponential Moving Average", [_line("dema", f"DEMA({period})", values, overlay=True)])


def _hma(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=300)
    half_period = max(1, period // 2)
    root_period = max(1, int(np.sqrt(period)))
    close = _close(df)
    raw = 2 * _wma(close, half_period) - _wma(close, period)
    values = _wma(raw, root_period)
    return _output("Hull Moving Average", [_line("hma", f"HMA({period})", values, overlay=True, color="#2962ff")])


def _vortex(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    positive = (high - low.shift(1)).abs().rolling(period, min_periods=period).sum()
    negative = (low - high.shift(1)).abs().rolling(period, min_periods=period).sum()
    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    range_sum = true_range.rolling(period, min_periods=period).sum().replace(0, np.nan)
    return _output("Vortex Indicator", [
        _line("vortex_positive", "VI+", positive / range_sum, color="#26a69a"),
        _line("vortex_negative", "VI-", negative / range_sum, color="#ef5350"),
    ])


def _ultimate_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    short = _integer(params, "short_period", 7, minimum=2, maximum=100)
    medium = _integer(params, "medium_period", 14, minimum=3, maximum=150)
    long = _integer(params, "long_period", 28, minimum=4, maximum=250)
    if not short < medium < long:
        raise ValueError("invalid parameter: period ordering")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous_close = close.shift(1)
    true_low = pd.concat([low, previous_close], axis=1).min(axis=1)
    true_high = pd.concat([high, previous_close], axis=1).max(axis=1)
    buying_pressure = close - true_low
    true_range = (true_high - true_low).clip(lower=0)

    def ratio(period: int) -> pd.Series:
        pressure_sum = buying_pressure.rolling(period, min_periods=period).sum()
        range_sum = true_range.rolling(period, min_periods=period).sum().replace(0, np.nan)
        return pressure_sum / range_sum

    values = (100 * (4 * ratio(short) + 2 * ratio(medium) + ratio(long)) / 7).clip(0, 100)
    return _output("Ultimate Oscillator", [_line("ultimate_oscillator", "Ultimate Oscillator", values)])


def _fisher(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=200)
    signal_period = _integer(params, "signal_period", 1, minimum=1, maximum=50)
    price = (_series(df, "high") + _series(df, "low")) / 2
    rolling_high = price.rolling(period, min_periods=period).max().to_numpy()
    rolling_low = price.rolling(period, min_periods=period).min().to_numpy()
    source = price.to_numpy()
    fisher = np.full(len(df), np.nan)
    previous_value = 0.0
    previous_fisher = 0.0
    for index in range(len(df)):
        if not np.isfinite(rolling_high[index]) or not np.isfinite(rolling_low[index]) or not np.isfinite(source[index]):
            continue
        width = rolling_high[index] - rolling_low[index]
        raw = 0.0 if width <= 0 else 2 * ((source[index] - rolling_low[index]) / width - 0.5)
        value = float(np.clip(0.33 * raw + 0.67 * previous_value, -0.999, 0.999))
        current = 0.5 * np.log((1 + value) / (1 - value)) + 0.5 * previous_fisher
        fisher[index] = current
        previous_value, previous_fisher = value, current
    fisher_series = pd.Series(fisher, index=df.index)
    signal = fisher_series.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output("Fisher Transform", [
        _line("fisher", "Fisher", fisher_series, color="#2962ff"),
        _line("fisher_signal", "Signal", signal, color="#ff6d00"),
    ])


def _force_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 13, minimum=1, maximum=200)
    raw = _close(df).diff() * _series(df, "volume").fillna(0).clip(lower=0)
    values = raw.ewm(span=period, adjust=False, min_periods=period).mean()
    return _output("Force Index", [_line("force_index", f"Force Index({period})", values)])


def _ease_of_movement(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    volume_divisor = _number(params, "volume_divisor", 10000, minimum=1, maximum=1_000_000_000)
    high, low = _series(df, "high"), _series(df, "low")
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    midpoint = (high + low) / 2
    box_ratio = (volume / volume_divisor) / (high - low).replace(0, np.nan)
    raw = midpoint.diff() / box_ratio.replace(0, np.nan)
    values = raw.rolling(period, min_periods=period).mean()
    return _output("Ease of Movement", [_line("ease_of_movement", f"EOM({period})", values, color="#26a69a")])


def _chaikin_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 3, minimum=1, maximum=100)
    slow = _integer(params, "slow_period", 10, minimum=2, maximum=200)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    multiplier = ((2 * close - high - low) / (high - low).replace(0, np.nan)).fillna(0)
    ad = (multiplier * volume).cumsum()
    values = ad.ewm(span=fast, adjust=False, min_periods=fast).mean() - ad.ewm(span=slow, adjust=False, min_periods=slow).mean()
    return _output("Chaikin Oscillator", [_line("chaikin_oscillator", "Chaikin Oscillator", values, color="#42a5f5")])


def _volume_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 5, minimum=2, maximum=100)
    slow = _integer(params, "slow_period", 20, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_period", 5, minimum=1, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    fast_average = volume.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_average = volume.ewm(span=slow, adjust=False, min_periods=slow).mean()
    oscillator = 100 * (fast_average - slow_average) / slow_average.replace(0, np.nan)
    signal = oscillator.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output("Volume Oscillator", [
        _line("volume_oscillator", "Volume Oscillator", oscillator, color="#26a69a"),
        _line("volume_oscillator_signal", "Signal", signal, color="#ff6d00"),
    ])


def _pvt(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    signal_period = _integer(params, "signal_period", 21, minimum=1, maximum=200)
    close = _close(df)
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    returns = (close / close.shift(1).replace(0, np.nan) - 1).replace([np.inf, -np.inf], np.nan).fillna(0)
    pvt = (returns * volume).cumsum()
    signal = pvt.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output("Price Volume Trend", [
        _line("pvt", "PVT", pvt, color="#2962ff"),
        _line("pvt_signal", "Signal", signal, color="#ff6d00"),
    ])


def _rvi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=100)
    movement = _series(df, "close") - _series(df, "open")
    bar_range = (_series(df, "high") - _series(df, "low")).clip(lower=0)
    weights = np.array([1.0, 2.0, 2.0, 1.0])
    weighted_move = movement.rolling(4, min_periods=4).apply(lambda values: float(np.dot(values, weights) / 6), raw=True)
    weighted_range = bar_range.rolling(4, min_periods=4).apply(lambda values: float(np.dot(values, weights) / 6), raw=True)
    vigor = weighted_move / weighted_range.replace(0, np.nan)
    signal = vigor.rolling(period, min_periods=period).mean()
    return _output("Relative Vigor Index", [
        _line("rvi", "RVI", vigor, color="#2962ff"),
        _line("rvi_signal", "Signal", signal, color="#ff6d00"),
    ])


def _choppiness(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    range_sum = true_range.rolling(period, min_periods=period).sum()
    span = (high.rolling(period, min_periods=period).max() - low.rolling(period, min_periods=period).min()).replace(0, np.nan)
    ratio = (range_sum / span).replace([np.inf, -np.inf], np.nan)
    values = (100 * np.log10(ratio) / np.log10(float(period))).replace([np.inf, -np.inf], np.nan).clip(0, 100)
    return _output("Choppiness Index", [_line("choppiness", f"CHOP({period})", values, color="#ab47bc")])


def _chip_distribution(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    """Build a price-level volume profile with candle-direction buy/sell estimates."""
    lookback = _integer(params, "lookback", 120, minimum=10, maximum=5000)
    row_count = _integer(params, "rows", 48, minimum=8, maximum=120)
    value_area_percent = _number(params, "value_area_percent", 70, minimum=50, maximum=99)
    value_area_ratio = value_area_percent / 100.0

    window = df.tail(lookback)
    ohlcv = {
        key: pd.to_numeric(window[key], errors="coerce").to_numpy(dtype=float)
        for key in ("open", "high", "low", "close", "volume")
    }
    valid = np.ones(len(window), dtype=bool)
    for key, values in ohlcv.items():
        valid &= np.isfinite(values)
    valid &= ohlcv["high"] >= ohlcv["low"]
    valid &= ohlcv["volume"] >= 0

    if not valid.any():
        raise ValueError("no valid bars for chip distribution")

    opens = ohlcv["open"][valid]
    highs = ohlcv["high"][valid]
    lows = ohlcv["low"][valid]
    closes = ohlcv["close"][valid]
    volumes = ohlcv["volume"][valid]
    price_low = float(np.min(lows))
    price_high = float(np.max(highs))
    if not np.isfinite(price_high - price_low):
        raise ValueError("chip distribution price range is out of range")

    if price_high <= price_low:
        padding = max(abs(price_low) * 1e-8, 1e-8)
        price_low -= padding
        price_high += padding

    edges = np.linspace(price_low, price_high, row_count + 1, dtype=float)
    buy_volume = np.zeros(row_count, dtype=float)
    sell_volume = np.zeros(row_count, dtype=float)

    for open_price, high, low, close, volume in zip(opens, highs, lows, closes, volumes):
        if volume <= 0:
            continue

        if high <= low:
            bin_index = int(np.clip(np.searchsorted(edges, close, side="right") - 1, 0, row_count - 1))
            buy_share = 1.0 if close > open_price else 0.0 if close < open_price else 0.5
            buy_volume[bin_index] += volume * buy_share
            sell_volume[bin_index] += volume * (1.0 - buy_share)
            continue

        first = max(0, int(np.searchsorted(edges, low, side="right") - 1))
        last = min(row_count - 1, int(np.searchsorted(edges, high, side="left")))
        overlaps = np.maximum(
            0.0,
            np.minimum(edges[first:last + 2], high) - np.maximum(edges[first:last + 2], low),
        )
        overlap_total = float(overlaps.sum())
        if overlap_total <= 0:
            bin_index = int(np.clip(np.searchsorted(edges, low + (high - low) / 2, side="right") - 1, 0, row_count - 1))
            overlaps = np.zeros(last - first + 1, dtype=float)
            overlaps[bin_index - first] = 1.0
            overlap_total = 1.0

        allocations = volume * (overlaps / overlap_total)
        # Keep each candle's assigned volume conserved despite floating-point rounding.
        allocations[-1] += volume - float(allocations.sum())
        if close > open_price:
            buy_volume[first:last + 1] += allocations
        elif close < open_price:
            sell_volume[first:last + 1] += allocations
        else:
            buy_volume[first:last + 1] += allocations * 0.5
            sell_volume[first:last + 1] += allocations * 0.5

    totals = buy_volume + sell_volume
    total_volume = float(totals.sum())
    if not np.isfinite(total_volume):
        raise ValueError("chip distribution volume is out of range")

    rows = []
    for index in range(row_count):
        rows.append({
            "priceLow": float(edges[index]),
            "priceHigh": float(edges[index + 1]),
            "price": float(edges[index] + (edges[index + 1] - edges[index]) / 2),
            "buyVolume": float(buy_volume[index]),
            "sellVolume": float(sell_volume[index]),
            "totalVolume": float(totals[index]),
        })

    poc_index = int(np.argmax(totals))
    target_volume = total_volume * value_area_ratio
    value_area_volume = float(totals[poc_index])
    value_area_low = poc_index
    value_area_high = poc_index
    while value_area_volume < target_volume and (value_area_low > 0 or value_area_high < row_count - 1):
        below = totals[value_area_low - 1] if value_area_low > 0 else -1.0
        above = totals[value_area_high + 1] if value_area_high < row_count - 1 else -1.0
        if above > below:
            value_area_high += 1
            value_area_volume += float(above)
        elif below > above:
            value_area_low -= 1
            value_area_volume += float(below)
        else:
            if value_area_low > 0:
                value_area_low -= 1
                value_area_volume += float(below)
            if value_area_high < row_count - 1 and value_area_volume < target_volume:
                value_area_high += 1
                value_area_volume += float(above)

    current_price = float(closes[-1])
    estimated_profitable_volume = 0.0
    for row in rows:
        if current_price >= row["priceHigh"]:
            estimated_profitable_volume += row["totalVolume"]
        elif current_price > row["priceLow"]:
            row_span = row["priceHigh"] - row["priceLow"]
            if row_span > 0:
                estimated_profitable_volume += row["totalVolume"] * (current_price - row["priceLow"]) / row_span

    profile = {
        "rows": rows,
        "windowBars": int(valid.sum()),
        "totalVolume": total_volume,
        "buyVolume": float(buy_volume.sum()),
        "sellVolume": float(sell_volume.sum()),
        "poc": rows[poc_index]["price"],
        "vah": rows[value_area_high]["priceHigh"],
        "val": rows[value_area_low]["priceLow"],
        "valueAreaPercent": value_area_percent,
        "currentPrice": current_price,
        "estimatedProfitableRatio": (
            float(np.clip(estimated_profitable_volume / total_volume, 0.0, 1.0))
            if total_volume > 0 else 0.0
        ),
        "method": "candle_direction_estimate",
    }
    return {"name": "Chip Distribution", "plots": [], "signals": [], "layers": [], "profile": profile}


def _qqe(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 14, minimum=2, maximum=100)
    rsi_smoothing = _integer(params, "rsi_smoothing", 5, minimum=1, maximum=50)
    factor = _number(params, "qqe_factor", 4.236, minimum=0.5, maximum=10)
    delta = _close(df).diff()
    gain = _wilder(delta.clip(lower=0).fillna(0), rsi_period)
    loss = _wilder((-delta.clip(upper=0)).fillna(0), rsi_period)
    rsi = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50).clip(0, 100)
    smoothed = _ema(rsi, rsi_smoothing)
    volatility = _ema(smoothed.diff().abs(), rsi_period)
    distance = factor * _ema(volatility, rsi_period)
    long_band = pd.Series(np.nan, index=df.index)
    short_band = pd.Series(np.nan, index=df.index)
    trend = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        value, width = smoothed.iloc[index], distance.iloc[index]
        if not np.isfinite(value) or not np.isfinite(width):
            continue
        lower, upper = value - width, value + width
        if index == 0 or not np.isfinite(long_band.iloc[index - 1]):
            long_band.iloc[index], short_band.iloc[index], trend[index] = lower, upper, 1
            continue
        long_band.iloc[index] = max(long_band.iloc[index - 1], lower) if smoothed.iloc[index - 1] > long_band.iloc[index - 1] and value > long_band.iloc[index - 1] else lower
        short_band.iloc[index] = min(short_band.iloc[index - 1], upper) if smoothed.iloc[index - 1] < short_band.iloc[index - 1] and value < short_band.iloc[index - 1] else upper
        trend[index] = 1 if value > short_band.iloc[index - 1] else -1 if value < long_band.iloc[index - 1] else trend[index - 1]
    trail = pd.Series(np.where(trend == 1, long_band, short_band), index=df.index)
    return _output("QQE Signals", [
        _line("qqe_rsi", "QQE RSI", smoothed),
        _line("qqe_trail", "QQE Trail", trail, color="#ff6d00"),
    ])


def _rmi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14, minimum=2, maximum=100)
    positive_threshold = _number(params, "pmom", 66, minimum=50, maximum=100)
    negative_threshold = _number(params, "nmom", 30, minimum=0, maximum=50)
    close = _close(df)
    delta = close.diff()
    gain = _wilder(delta.clip(lower=0).fillna(0), period)
    loss = _wilder((-delta.clip(upper=0)).fillna(0), period)
    rsi = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)
    typical = (_series(df, "high") + _series(df, "low") + close) / 3
    flow = typical * _series(df, "volume").fillna(0)
    direction = typical.diff()
    positive = flow.where(direction > 0, 0).rolling(period, min_periods=period).sum()
    negative = flow.where(direction < 0, 0).rolling(period, min_periods=period).sum()
    mfi = (100 - 100 / (1 + positive / negative.replace(0, np.nan))).fillna(50)
    rmi = ((rsi + mfi) / 2).to_numpy(dtype=float)
    close_values = close.to_numpy(dtype=float)
    ema5 = close.ewm(span=5, adjust=False, min_periods=5).mean().to_numpy(dtype=float)
    ema_change = np.full(len(df), np.nan)
    if len(df) > 1:
        ema_change[1:] = ema5[1:] - ema5[:-1]
    positive = np.zeros(len(df), dtype=bool)
    negative = np.zeros(len(df), dtype=bool)
    long_signal = np.zeros(len(df), dtype=bool)
    short_signal = np.zeros(len(df), dtype=bool)
    for index in range(len(df)):
        prev = rmi[index - 1] if index else np.nan
        if np.isfinite(prev) and np.isfinite(rmi[index]) and np.isfinite(ema_change[index]) and prev < positive_threshold and rmi[index] > positive_threshold and rmi[index] > negative_threshold and ema_change[index] > 0:
            positive[index], long_signal[index] = True, True
        elif np.isfinite(rmi[index]) and np.isfinite(ema_change[index]) and rmi[index] < negative_threshold and ema_change[index] < 0:
            negative[index], short_signal[index] = True, True
        elif index:
            positive[index], negative[index] = positive[index - 1], negative[index - 1]
    high, low = _series(df, "high"), _series(df, "low")
    atr = _atr(df, 30)
    band_source = pd.concat([atr * 0.3, close * 0.003], axis=1).min(axis=1).shift(20) * 4
    price_range = (high - low).clip(lower=0)
    range_sum = price_range.rolling(20, min_periods=20).sum()
    weighted_sum = (close * price_range).rolling(20, min_periods=20).sum()
    rwma = weighted_sum / range_sum.replace(0, np.nan)
    rwma_up = rwma - band_source
    rwma_down = rwma + band_source
    plots = [
        _line("rmi_up", "RMI Trend Up", rwma_up.where(positive), overlay=True, color="#00bcd4"),
        _line("rmi_down", "RMI Trend Down", rwma_down.where(negative), overlay=True, color="#ff5252"),
        _line("rmi_up_upper", "Upper Up Band", (rwma_up + band_source).where(positive), overlay=True, color="#80deea"),
        _line("rmi_up_lower", "Lower Up Band", (rwma_up - band_source).where(positive), overlay=True, color="#80deea"),
        _line("rmi_down_upper", "Upper Down Band", (rwma_down + band_source).where(negative), overlay=True, color="#ef9a9a"),
        _line("rmi_down_lower", "Lower Down Band", (rwma_down - band_source).where(negative), overlay=True, color="#ef9a9a"),
    ]
    buys = [float(low.iloc[index]) * 0.995 if long_signal[index] and np.isfinite(low.iloc[index]) else None for index in range(len(df))]
    sells = [float(high.iloc[index]) * 1.005 if short_signal[index] and np.isfinite(high.iloc[index]) else None for index in range(len(df))]
    return {
        **_output("RMI Trend Sniper", plots),
        "signals": [
            {"type": "buy", "text": "RMI+", "data": buys, "color": "#00e676"},
            {"type": "sell", "text": "RMI-", "data": sells, "color": "#ff5252"},
        ],
    }


def _stc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 23, minimum=2, maximum=150)
    slow = _integer(params, "slow_period", 50, minimum=3, maximum=250)
    cycle = _integer(params, "cycle_period", 10, minimum=2, maximum=100)
    smoothing = _number(params, "smoothing", 0.5, minimum=0.1, maximum=1)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    macd = _ema(close, fast) - _ema(close, slow)
    minimum = macd.rolling(cycle, min_periods=cycle).min()
    maximum = macd.rolling(cycle, min_periods=cycle).max()
    width = maximum - minimum
    raw = (100 * (macd - minimum) / width.replace(0, np.nan)).where(width != 0, 50)
    first = pd.Series(np.nan, index=df.index)
    previous = 50.0
    for index, value in enumerate(raw):
        if np.isfinite(value):
            previous = smoothing * float(value) + (1 - smoothing) * previous
            first.iloc[index] = previous
    low = first.rolling(cycle, min_periods=cycle).min()
    high = first.rolling(cycle, min_periods=cycle).max()
    second_width = high - low
    second_raw = (100 * (first - low) / second_width.replace(0, np.nan)).where(second_width != 0, 50)
    result = pd.Series(np.nan, index=df.index)
    previous = 50.0
    for index, value in enumerate(second_raw):
        if np.isfinite(value):
            previous = smoothing * float(value) + (1 - smoothing) * previous
            result.iloc[index] = previous
    return _output("Schaff Trend Cycle", [_line("stc", "STC", result, color="#2962ff")])


def _tsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    long = _integer(params, "long_period", 25, minimum=2, maximum=200)
    short = _integer(params, "short_period", 13, minimum=2, maximum=100)
    signal_period = _integer(params, "signal_period", 7, minimum=2, maximum=100)
    momentum = _close(df).diff()
    smooth = lambda values: _ema(_ema(values, long), short)
    denominator = smooth(momentum.abs()).replace(0, np.nan)
    tsi = (100 * smooth(momentum) / denominator).replace([np.inf, -np.inf], np.nan)
    signal = _ema(tsi, signal_period)
    return _output("True Strength Index", [_line("tsi", "TSI", tsi), _line("tsi_signal", "Signal", signal, color="#ff6d00")])


def _connors_rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 3, minimum=2, maximum=50)
    streak_period = _integer(params, "streak_rsi_period", 2, minimum=2, maximum=50)
    rank_period = _integer(params, "rank_period", 100, minimum=5, maximum=200)
    close = _close(df)

    def rsi(values: pd.Series, period: int) -> pd.Series:
        delta = values.diff()
        gain = _wilder(delta.clip(lower=0).fillna(0), period)
        loss = _wilder((-delta.clip(upper=0)).fillna(0), period)
        return (100 * gain / (gain + loss).replace(0, np.nan)).fillna(50).clip(0, 100)

    change = close.diff().to_numpy()
    streak_values = np.zeros(len(df))
    for index in range(1, len(df)):
        streak_values[index] = (streak_values[index - 1] + 1 if streak_values[index - 1] > 0 else 1) if change[index] > 0 else (streak_values[index - 1] - 1 if streak_values[index - 1] < 0 else -1) if change[index] < 0 else 0
    streak_rsi = rsi(pd.Series(streak_values, index=df.index), streak_period)
    returns = close.pct_change(fill_method=None).to_numpy() * 100
    rank = np.full(len(df), np.nan)
    for index in range(rank_period + 1, len(df)):
        prior = returns[index - rank_period:index]
        if np.isfinite(returns[index]) and np.isfinite(prior).all():
            rank[index] = 100 * np.sum(prior < returns[index]) / rank_period
    values = (rsi(close, rsi_period).to_numpy() + streak_rsi.to_numpy() + rank) / 3
    return _output("Connors RSI", [_line("connors_rsi", "Connors RSI", values, color="#7e57c2")])


def _coppock(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    long = _integer(params, "long_roc", 14, minimum=2, maximum=200)
    short = _integer(params, "short_roc", 11, minimum=2, maximum=200)
    wma_period = _integer(params, "wma_period", 10, minimum=2, maximum=100)
    if long == short:
        raise ValueError("invalid parameter: roc periods")
    close = _close(df)
    roc = 100 * ((close / close.shift(long) - 1) + (close / close.shift(short) - 1))
    weights = np.arange(1, wma_period + 1, dtype=float)
    values = roc.rolling(wma_period, min_periods=wma_period).apply(lambda window: float(np.dot(window, weights) / weights.sum()), raw=True)
    return _output("Coppock Curve", [_line("coppock", "Coppock Curve", values, color="#2962ff")])


def _dpo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    offset = period // 2 + 1
    average = _close(df).rolling(period, min_periods=period).mean().shift(offset)
    return _output("Detrended Price Oscillator", [_line("dpo", f"DPO({period})", _close(df) - average, color="#2962ff")])


def _mass_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    ema_period = _integer(params, "ema_period", 9, minimum=2, maximum=100)
    sum_period = _integer(params, "sum_period", 25, minimum=2, maximum=200)
    bar_range = (_series(df, "high") - _series(df, "low")).clip(lower=0)
    first = _ema(bar_range, ema_period)
    second = _ema(first, ema_period)
    values = (first / second.replace(0, np.nan)).rolling(sum_period, min_periods=sum_period).sum()
    return _output("Mass Index", [_line("mass_index", "Mass Index", values, color="#ab47bc")])


def _ulcer_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    close = _close(df)
    high = close.rolling(period, min_periods=period).max()
    drawdown = 100 * (close / high.replace(0, np.nan) - 1)
    values = drawdown.pow(2).rolling(period, min_periods=period).mean().pow(0.5)
    return _output("Ulcer Index", [_line("ulcer_index", "Ulcer Index", values, color="#ef5350")])


def _klinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 34, minimum=2, maximum=200)
    slow = _integer(params, "slow_period", 55, minimum=3, maximum=250)
    signal_period = _integer(params, "signal_period", 13, minimum=2, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    high = _series(df, "high").to_numpy()
    low = _series(df, "low").to_numpy()
    close = _close(df).to_numpy()
    volume = _series(df, "volume").fillna(0).clip(lower=0).to_numpy()
    force = np.full(len(df), np.nan)
    trend, previous_range, cumulative_range, previous_sum = 0.0, 0.0, 0.0, np.nan
    for index in range(len(df)):
        price_sum = high[index] + low[index] + close[index]
        bar_range = max(0.0, high[index] - low[index])
        if not np.isfinite(price_sum):
            continue
        current_trend = 1.0 if not np.isfinite(previous_sum) or price_sum >= previous_sum else -1.0
        cumulative_range = cumulative_range + bar_range if trend == 0 or current_trend == trend else previous_range + bar_range
        if cumulative_range > 0:
            force[index] = volume[index] * abs(2 * bar_range / cumulative_range - 1) * current_trend * 100
        trend, previous_range, previous_sum = current_trend, bar_range, price_sum
    force_series = pd.Series(force, index=df.index)
    kvo = _ema(force_series, fast) - _ema(force_series, slow)
    signal = _ema(kvo, signal_period)
    return _output("Klinger Volume Oscillator", [_line("kvo", "KVO", kvo), _line("kvo_signal", "Signal", signal, color="#ff6d00")])


def _ppo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 12, minimum=2, maximum=100)
    slow = _integer(params, "slow_period", 26, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_period", 9, minimum=2, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    slow_ema = _ema(close, slow)
    ppo = 100 * (_ema(close, fast) - slow_ema) / slow_ema.replace(0, np.nan)
    signal = _ema(ppo, signal_period)
    return _output("Percentage Price Oscillator", [
        _line("ppo", "PPO", ppo),
        _line("ppo_signal", "Signal", signal, color="#ff6d00"),
        _bar("ppo_histogram", "Histogram", ppo - signal, color="#26a69a"),
    ])


def _volume_macd(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_length", 12, minimum=2, maximum=100)
    slow = _integer(params, "slow_length", 26, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_length", 9, minimum=2, maximum=100)
    show_histogram = bool(params.get("histogram", True))
    if fast >= slow:
        raise ValueError("invalid parameter: fast_length")
    close = _close(df)
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    volume_sum = volume.rolling(slow, min_periods=1).sum()
    weighted_price = ((close * volume).rolling(slow, min_periods=1).sum() / volume_sum.replace(0, np.nan)).fillna(close)
    macd = _ema(weighted_price, fast) - _ema(weighted_price, slow)
    signal = _ema(macd, signal_period)
    plots = [_line("volume_macd", "VW MACD", macd, color="#26a69a"), _line("volume_macd_signal", "Signal", signal, color="#ffb300")]
    plots.append(_bar("volume_macd_histogram", "Histogram", macd - signal if show_histogram else np.full(len(df), np.nan), color="#90caf9"))
    macd_values, signal_values = macd.to_numpy(), signal.to_numpy()
    previous_macd = np.concatenate(([np.nan], macd_values[:-1]))
    previous_signal = np.concatenate(([np.nan], signal_values[:-1]))
    finite = np.isfinite(macd_values) & np.isfinite(signal_values) & np.isfinite(previous_macd) & np.isfinite(previous_signal)
    buy = finite & (previous_macd <= previous_signal) & (macd_values > signal_values)
    sell = finite & (previous_macd >= previous_signal) & (macd_values < signal_values)
    return {**_output("Volume Weighted MACD", plots), "signals": [
        {"type": "buy", "text": "VW MACD+", "data": [float(value) if flag else None for value, flag in zip(macd_values, buy)], "color": "#00c853"},
        {"type": "sell", "text": "VW MACD-", "data": [float(value) if flag else None for value, flag in zip(macd_values, sell)], "color": "#ff1744"},
    ]}


def _bop(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "smooth_period", 1, minimum=1, maximum=100)
    open_price, high, low, close = (_series(df, key) for key in ("open", "high", "low", "close"))
    values = ((close - open_price) / (high - low).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).where(high != low, 0).clip(-1, 1)
    if period > 1:
        values = values.rolling(period, min_periods=period).mean()
    return _output("Balance of Power", [_line("bop", "BOP", values, color="#26a69a")])


def _rvi_volatility(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    close = _close(df)
    change = close.diff()
    volatility = close.rolling(period, min_periods=period).std(ddof=0)
    up = volatility.where(change > 0, 0)
    down = volatility.where(change < 0, 0)
    up_average = _wilder(up, period)
    down_average = _wilder(down, period)
    total = up_average + down_average
    values = (100 * up_average / total.replace(0, np.nan)).where(total != 0, 50).clip(0, 100)
    return _output("Relative Volatility Index", [_line("rvi_volatility", "RVI", values, color="#7e57c2")])


def _elder_ray(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 13, minimum=2, maximum=200)
    baseline = _ema(_close(df), period)
    return _output("Elder Ray Index", [
        _line("bull_power", "Bull Power", _series(df, "high") - baseline, color="#26a69a"),
        _line("bear_power", "Bear Power", _series(df, "low") - baseline, color="#ef5350"),
    ])


def _kama(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=100)
    fast = _integer(params, "fast_period", 2, minimum=1, maximum=50)
    slow = _integer(params, "slow_period", 30, minimum=2, maximum=200)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    efficiency = (close.diff(period).abs() / close.diff().abs().rolling(period, min_periods=period).sum().replace(0, np.nan)).fillna(0)
    fast_sc, slow_sc = 2 / (fast + 1), 2 / (slow + 1)
    smoothing = (efficiency * (fast_sc - slow_sc) + slow_sc) ** 2
    values = pd.Series(np.nan, index=df.index)
    if len(close) > period:
        values.iloc[period] = close.iloc[period]
        for index in range(period + 1, len(close)):
            values.iloc[index] = values.iloc[index - 1] + smoothing.iloc[index] * (close.iloc[index] - values.iloc[index - 1])
    return _output("Kaufman Adaptive Moving Average", [_line("kama", f"KAMA({period})", values, overlay=True, color="#ab47bc")])


def _vidya(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    momentum_period = _integer(params, "momentum_period", 9, minimum=2, maximum=100)
    signal_period = _integer(params, "signal_period", 9, minimum=2, maximum=100)
    close = _close(df)
    change = close.diff()
    up = change.clip(lower=0).rolling(momentum_period, min_periods=momentum_period).sum()
    down = (-change.clip(upper=0)).rolling(momentum_period, min_periods=momentum_period).sum()
    ratio = ((up - down).abs() / (up + down).replace(0, np.nan)).fillna(0).to_numpy()
    values = np.full(len(df), np.nan)
    close_values = close.to_numpy()
    alpha = 2 / (period + 1)
    for index, value in enumerate(close_values):
        if not np.isfinite(value):
            continue
        current_alpha = alpha * min(1, max(0, ratio[index]))
        values[index] = value if index == 0 or not np.isfinite(values[index - 1]) else current_alpha * value + (1 - current_alpha) * values[index - 1]
    vidya = pd.Series(values, index=df.index)
    return _output("Variable Moving Average", [
        _line("vidya", "VIDYA", vidya, overlay=True, color="#2962ff"),
        _line("vidya_signal", "VIDYA Signal", _ema(vidya, signal_period), overlay=True, color="#ff6d00"),
    ])


def _half_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    amplitude = _integer(params, "amplitude", 2, minimum=1, maximum=30)
    atr_period = _integer(params, "atr_period", 100, minimum=2, maximum=200)
    deviation = _number(params, "channel_deviation", 2, minimum=0.25, maximum=6)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    atr = _atr(df, atr_period).to_numpy()
    prior_high = high.rolling(amplitude, min_periods=amplitude).max().shift(1).to_numpy()
    prior_low = low.rolling(amplitude, min_periods=amplitude).min().shift(1).to_numpy()
    trend = np.zeros(len(df), dtype=int)
    line = np.full(len(df), np.nan)
    upper = np.full(len(df), np.nan)
    lower = np.full(len(df), np.nan)
    for index in range(len(df)):
        trend[index] = trend[index - 1] if index else 1
        if np.isfinite(prior_high[index]) and close.iloc[index] > prior_high[index]: trend[index] = 1
        elif np.isfinite(prior_low[index]) and close.iloc[index] < prior_low[index]: trend[index] = -1
        if np.isfinite(atr[index]):
            center = prior_low[index] if trend[index] > 0 else prior_high[index]
            center = close.iloc[index] if not np.isfinite(center) else center
            line[index] = max(center, line[index - 1]) if index and trend[index] == trend[index - 1] == 1 and np.isfinite(line[index - 1]) else min(center, line[index - 1]) if index and trend[index] == trend[index - 1] == -1 and np.isfinite(line[index - 1]) else center
            upper[index], lower[index] = line[index] + deviation * atr[index], line[index] - deviation * atr[index]
    previous = np.concatenate(([0], trend[:-1]))
    buys = (trend == 1) & (previous == -1)
    sells = (trend == -1) & (previous == 1)
    return {**_output("HalfTrend", [_line("half_trend", "HalfTrend", line, overlay=True, color="#2962ff"), _line("half_trend_upper", "Upper", upper, overlay=True, color="#26a69a"), _line("half_trend_lower", "Lower", lower, overlay=True, color="#ef5350")]), "signals": [
        {"type": "buy", "text": "HT+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "HT-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _gaussian_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    poles = _integer(params, "poles", 3, minimum=1, maximum=6)
    atr_period = _integer(params, "atr_period", 14, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 1.5, minimum=0.25, maximum=8)
    center = _close(df)
    for _ in range(poles):
        center = center.ewm(span=period, adjust=False, min_periods=period).mean()
    atr = _atr(df, atr_period)
    close = _close(df).to_numpy()
    center_values, atr_values = center.to_numpy(), atr.to_numpy()
    trend = np.zeros(len(df), dtype=int)
    trend_line = np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(center_values[index]) or not np.isfinite(atr_values[index]):
            continue
        upper = center_values[index] + multiplier * atr_values[index]
        lower = center_values[index] - multiplier * atr_values[index]
        if index == 0 or trend[index - 1] == 0:
            trend[index] = 1 if close[index] >= center_values[index] else -1
        elif trend[index - 1] > 0:
            trend[index] = -1 if close[index] < lower else 1
        else:
            trend[index] = 1 if close[index] > upper else -1
        trend_line[index] = lower if trend[index] > 0 else upper
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    low, high = _series(df, "low"), _series(df, "high")
    return {**_output("Gaussian Filter Trend", [
        _line("gaussian_filter", "Gaussian Filter", center, overlay=True, color="#2962ff"),
        _line("gaussian_trend", "Gaussian Trend", trend_line, overlay=True, color="#ffb300"),
    ]), "signals": [
        {"type": "buy", "text": "GF+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "GF-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _atr_trailing_stop(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "atr_length", 14, minimum=2, maximum=100)
    multiplier = _number(params, "atr_multiplier", 3, minimum=0.5, maximum=8)
    source_name = str(params.get("source", "close")).lower()
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    source = (high + low) / 2 if source_name == "hl2" else close
    source_values = source.to_numpy()
    atr_values = _atr(df, period).to_numpy()
    high_values, low_values = high.to_numpy(), low.to_numpy()
    long_stop, short_stop = np.full(len(df), np.nan), np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(source_values[index]) or not np.isfinite(atr_values[index]):
            continue
        long_candidate = source_values[index] - multiplier * atr_values[index]
        short_candidate = source_values[index] + multiplier * atr_values[index]
        prev_direction = direction[index - 1] if index else 0
        prev_long = long_stop[index - 1] if index else np.nan
        prev_short = short_stop[index - 1] if index else np.nan
        if prev_direction >= 0:
            direction[index] = 1 if prev_direction == 0 or source_values[index] >= prev_long else -1
        else:
            direction[index] = -1 if source_values[index] <= prev_short else 1
        if direction[index] > 0:
            long_stop[index] = max(prev_long, long_candidate) if np.isfinite(prev_long) and prev_direction > 0 else long_candidate
            short_stop[index] = short_candidate
        else:
            short_stop[index] = min(prev_short, short_candidate) if np.isfinite(prev_short) and prev_direction < 0 else short_candidate
            long_stop[index] = long_candidate
    active = np.where(direction > 0, long_stop, short_stop)
    previous_direction = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction > 0) & (previous_direction <= 0), (direction < 0) & (previous_direction >= 0)
    return {**_output("ATR Trailing Stop", [
        _line("atr_stop", "ATR Stop", active, overlay=True, color="#ffb300"),
        _line("atr_long_stop", "Long Stop", long_stop, overlay=True, color="#26a69a"),
        _line("atr_short_stop", "Short Stop", short_stop, overlay=True, color="#ef5350"),
    ]), "signals": [
        {"type": "buy", "text": "ATR Buy", "data": [float(low_values[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00c853"},
        {"type": "sell", "text": "ATR Sell", "data": [float(high_values[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff1744"},
    ]}


def _chandelier(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 22, minimum=5, maximum=100)
    multiplier = _number(params, "atr_multiplier", 3, minimum=1, maximum=6)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    atr = _atr(df, period)
    long_candidate = high.rolling(period, min_periods=period).max() - multiplier * atr
    short_candidate = low.rolling(period, min_periods=period).min() + multiplier * atr
    trend = np.zeros(len(df), dtype=int)
    stop = np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(long_candidate.iloc[index]) or not np.isfinite(short_candidate.iloc[index]):
            continue
        previous_trend = trend[index - 1] if index else 0
        previous_stop = stop[index - 1] if index else np.nan
        if previous_trend == 0:
            trend[index] = 1 if close.iloc[index] >= (long_candidate.iloc[index] + short_candidate.iloc[index]) / 2 else -1
            stop[index] = long_candidate.iloc[index] if trend[index] > 0 else short_candidate.iloc[index]
        elif previous_trend > 0:
            trend[index] = -1 if close.iloc[index] < previous_stop else 1
            stop[index] = short_candidate.iloc[index] if trend[index] < 0 else max(previous_stop, long_candidate.iloc[index])
        else:
            trend[index] = 1 if close.iloc[index] > previous_stop else -1
            stop[index] = long_candidate.iloc[index] if trend[index] > 0 else min(previous_stop, short_candidate.iloc[index])
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous != 1), (trend == -1) & (previous != -1)
    return {**_output("Chandelier Exit", [_line("chandelier_stop", "Chandelier Stop", stop, overlay=True, color="#ffb300")]), "signals": [
        {"type": "buy", "text": "CE+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "CE-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _atr_rope(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "atr_period", 14, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 1.5, minimum=0.25, maximum=8)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    atr = _atr(df, period).to_numpy()
    closes = close.to_numpy()
    rope = np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(atr[index]):
            continue
        threshold = atr[index] * multiplier
        if index == 0 or not np.isfinite(rope[index - 1]):
            rope[index] = closes[index]
            continue
        previous = rope[index - 1]
        if closes[index] > previous + threshold:
            rope[index], direction[index] = closes[index] - threshold, 1
        elif closes[index] < previous - threshold:
            rope[index], direction[index] = closes[index] + threshold, -1
        else:
            rope[index], direction[index] = previous, direction[index - 1]
    previous = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction == 1) & (previous != 1), (direction == -1) & (previous != -1)
    return {**_output("ATR Rope", [_line("atr_rope", "ATR Rope", rope, overlay=True, color="#26a69a")]), "signals": [
        {"type": "buy", "text": "Rope+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "Rope-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _pmax(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    ma_period = _integer(params, "ma_period", 10, minimum=5, maximum=60)
    atr_period = _integer(params, "atr_period", 10, minimum=5, maximum=60)
    multiplier = _number(params, "atr_multiplier", 3, minimum=1, maximum=6)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    baseline, atr = _ema(close, ma_period), _atr(df, atr_period)
    long_basic, short_basic = baseline - multiplier * atr, baseline + multiplier * atr
    long_stop, short_stop, pmax = np.full(len(df), np.nan), np.full(len(df), np.nan), np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(long_basic.iloc[index]) or not np.isfinite(short_basic.iloc[index]):
            continue
        if index == 0 or direction[index - 1] == 0 or not np.isfinite(long_stop[index - 1]) or not np.isfinite(short_stop[index - 1]):
            long_stop[index], short_stop[index] = long_basic.iloc[index], short_basic.iloc[index]
            direction[index] = 1 if close.iloc[index] >= baseline.iloc[index] else -1
        else:
            long_stop[index] = max(long_basic.iloc[index], long_stop[index - 1]) if baseline.iloc[index - 1] > long_stop[index - 1] else long_basic.iloc[index]
            short_stop[index] = min(short_basic.iloc[index], short_stop[index - 1]) if baseline.iloc[index - 1] < short_stop[index - 1] else short_basic.iloc[index]
            direction[index] = 1 if direction[index - 1] == -1 and baseline.iloc[index] > short_stop[index - 1] else -1 if direction[index - 1] == 1 and baseline.iloc[index] < long_stop[index - 1] else direction[index - 1]
        pmax[index] = long_stop[index] if direction[index] == 1 else short_stop[index]
    previous = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction == 1) & (previous == -1), (direction == -1) & (previous == 1)
    return {**_output("PMax Trend Filter", [_line("pmax_baseline", "EMA Baseline", baseline, overlay=True, color="#ffb300"), _line("pmax_up", "PMax Up", np.where(direction == 1, pmax, np.nan), overlay=True, color="#00e676"), _line("pmax_down", "PMax Down", np.where(direction == -1, pmax, np.nan), overlay=True, color="#ff5252")]), "signals": [
        {"type": "buy", "text": "PMax+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "PMax-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _range_filter(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "sampling_period", 50, minimum=10, maximum=150)
    multiplier = _number(params, "range_multiplier", 3, minimum=1, maximum=6)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    smooth_range = _ema(close.diff().abs().fillna(0), period)
    smooth_range = _ema(smooth_range, max(1, period * 2 - 1)) * multiplier
    closes, ranges = close.to_numpy(), smooth_range.to_numpy()
    filt = np.full(len(df), np.nan)
    up_count, down_count = np.zeros(len(df)), np.zeros(len(df))
    if len(df):
        filt[0] = closes[0]
    for index in range(1, len(df)):
        current_range = ranges[index] if np.isfinite(ranges[index]) else 0
        filt[index] = max(filt[index - 1], closes[index] - current_range) if closes[index] > filt[index - 1] else min(filt[index - 1], closes[index] + current_range)
        if filt[index] > filt[index - 1]:
            up_count[index], down_count[index] = up_count[index - 1] + 1, 0
        elif filt[index] < filt[index - 1]:
            down_count[index], up_count[index] = down_count[index - 1] + 1, 0
        else:
            up_count[index], down_count[index] = up_count[index - 1], down_count[index - 1]
    upper, lower = filt + ranges, filt - ranges
    long_condition, short_condition = (closes > filt) & (up_count > 0), (closes < filt) & (down_count > 0)
    previous_long, previous_short = np.concatenate(([False], long_condition[:-1])), np.concatenate(([False], short_condition[:-1]))
    buys, sells = long_condition & ~previous_long, short_condition & ~previous_short
    return {**_output("Range Filter", [_line("range_filter", "Range Filter", filt, overlay=True, color="#00bcd4"), _line("range_upper", "Upper Range", upper, overlay=True, color="#90caf9"), _line("range_lower", "Lower Range", lower, overlay=True, color="#90caf9")]), "signals": [
        {"type": "buy", "text": "RF+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "RF-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _vwap_channel(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 30, minimum=5, maximum=200)
    deviation = _number(params, "deviation", 1.5, minimum=0.25, maximum=5)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    typical = (high + low + close) / 3
    total = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    vwap = (typical * volume).rolling(period, min_periods=period).sum() / total
    variance = ((typical * typical * volume).rolling(period, min_periods=period).sum() / total - vwap * vwap).clip(lower=0)
    std = variance.pow(0.5)
    return _output("VWAP Price Channel", [_line("vwap_channel", "VWAP", vwap, overlay=True, color="#2962ff"), _line("vwap_upper", "VWAP Upper", vwap + deviation * std, overlay=True, color="#ab47bc"), _line("vwap_lower", "VWAP Lower", vwap - deviation * std, overlay=True, color="#ab47bc")])


def _turtle(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    entry = _integer(params, "entry_length", 20, minimum=5, maximum=100)
    exit_period = _integer(params, "exit_length", 10, minimum=2, maximum=50)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    entry_upper = high.rolling(entry, min_periods=entry).max().shift(1)
    entry_lower = low.rolling(entry, min_periods=entry).min().shift(1)
    exit_upper = high.rolling(exit_period, min_periods=exit_period).max().shift(1)
    exit_lower = low.rolling(exit_period, min_periods=exit_period).min().shift(1)
    closes = close.to_numpy()
    long_condition, short_condition = closes > entry_upper.to_numpy(), closes < entry_lower.to_numpy()
    previous_long, previous_short = np.concatenate(([False], long_condition[:-1])), np.concatenate(([False], short_condition[:-1]))
    buys, sells = long_condition & ~previous_long, short_condition & ~previous_short
    return {**_output("Turtle Trade Channels", [_line("turtle_entry_upper", "Entry Upper", entry_upper, overlay=True, color="#26a69a"), _line("turtle_entry_lower", "Entry Lower", entry_lower, overlay=True, color="#ef5350"), _line("turtle_exit_upper", "Exit Upper", exit_upper, overlay=True, color="#80cbc4"), _line("turtle_exit_lower", "Exit Lower", exit_lower, overlay=True, color="#ef9a9a")]), "signals": [
        {"type": "buy", "text": "Turtle+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "Turtle-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _nrtr(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    percentage = _number(params, "percentage", 1, minimum=0.25, maximum=5)
    volatility_multiplier = _number(params, "mult", 0, minimum=0, maximum=3)
    period = _integer(params, "length", 20, minimum=5, maximum=100)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    closes = close.to_numpy()
    average = close.rolling(period, min_periods=period).mean().to_numpy()
    std = close.rolling(period, min_periods=period).std(ddof=0).to_numpy()
    long_stop, short_stop, trend = np.full(len(df), np.nan), np.full(len(df), np.nan), np.zeros(len(df), dtype=int)
    peak = trough = active = np.nan
    for index in range(len(df)):
        if index < period or not np.isfinite(closes[index]):
            continue
        rate = percentage / 100
        if volatility_multiplier > 0 and np.isfinite(average[index]) and average[index] != 0 and np.isfinite(std[index]):
            rate = max(0.0001, std[index] * volatility_multiplier / abs(average[index]))
        if (trend[index - 1] >= 0 if index else True):
            peak = closes[index] if not np.isfinite(peak) else max(peak, closes[index])
            active = peak * (1 - rate)
            if closes[index] <= active:
                trend[index], trough, active = -1, closes[index], closes[index] * (1 + rate)
                short_stop[index] = active
            else:
                trend[index] = 1
                long_stop[index] = max(active, long_stop[index - 1]) if index and np.isfinite(long_stop[index - 1]) else active
        else:
            trough = closes[index] if not np.isfinite(trough) else min(trough, closes[index])
            active = trough * (1 + rate)
            if closes[index] >= active:
                trend[index], peak, active = 1, closes[index], closes[index] * (1 - rate)
                long_stop[index] = active
            else:
                trend[index] = -1
                short_stop[index] = min(active, short_stop[index - 1]) if index and np.isfinite(short_stop[index - 1]) else active
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    return {**_output("NRTR", [_line("nrtr_long", "NRTR Long Stop", long_stop, overlay=True, color="#00e676"), _line("nrtr_short", "NRTR Short Stop", short_stop, overlay=True, color="#ff5252")]), "signals": [
        {"type": "buy", "text": "NRTR+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "NRTR-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _trend_state(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20, minimum=2, maximum=200)
    multiplier = _number(params, "multiplier", 3.5, minimum=0.1, maximum=10)
    source_name = str(params.get("src_type", "close")).lower()
    open_price, high, low, close = (_series(df, key).to_numpy() for key in ("open", "high", "low", "close"))
    source = {"hl2": (high + low) / 2, "hlc3": (high + low + close) / 3, "ohlc4": (open_price + high + low + close) / 4}.get(source_name, close)
    movement = np.full(len(df), np.nan)
    if len(df) > 1:
        movement[1:] = np.abs(np.diff(source))
    movement_rma = _wilder(pd.Series(movement, index=df.index), period).to_numpy()
    adaptive_range = movement_rma * multiplier
    filter_line = np.full(len(df), np.nan)
    trend = np.zeros(len(df), dtype=int)
    for index in range(period, len(df)):
        if not np.isfinite(source[index]) or not np.isfinite(adaptive_range[index]):
            if index > period:
                filter_line[index], trend[index] = filter_line[index - 1], trend[index - 1]
            continue
        if index == period or not np.isfinite(filter_line[index - 1]):
            filter_line[index] = source[index]
            continue
        previous = filter_line[index - 1]
        if source[index] > previous + adaptive_range[index]:
            filter_line[index] = source[index] - adaptive_range[index]
        elif source[index] < previous - adaptive_range[index]:
            filter_line[index] = source[index] + adaptive_range[index]
        else:
            filter_line[index] = previous
        trend[index] = 1 if filter_line[index] > previous else -1 if filter_line[index] < previous else trend[index - 1]
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    low, high = _series(df, "low"), _series(df, "high")
    return {**_output("Trend State Signals", [_line("trend_state_filter", "Step Filter", filter_line, overlay=True, color="#26a69a")]), "signals": [
        {"type": "buy", "text": "TSS+", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "TSS-", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _zero_lag_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 70, minimum=2, maximum=300)
    multiplier = _number(params, "mult", 1.2, minimum=0.1, maximum=10)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    lag = max(1, (period - 1) // 2)
    zlema = _ema(close + (close - close.shift(lag)), period).to_numpy()
    atr = _atr(df, period)
    volatility = atr.rolling(period * 3, min_periods=period * 3).max().mul(multiplier).to_numpy()
    closes = close.to_numpy()
    upper, lower = zlema + volatility, zlema - volatility
    trend = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(zlema[index]) or not np.isfinite(upper[index]) or not np.isfinite(lower[index]) or not np.isfinite(closes[index]):
            continue
        if index == 0 or trend[index - 1] == 0:
            trend[index] = 1 if closes[index] >= zlema[index] else -1
        elif index and np.isfinite(upper[index - 1]) and closes[index - 1] <= upper[index - 1] and closes[index] > upper[index - 1]:
            trend[index] = 1
        elif index and np.isfinite(lower[index - 1]) and closes[index - 1] >= lower[index - 1] and closes[index] < lower[index - 1]:
            trend[index] = -1
        else:
            trend[index] = trend[index - 1]
    bull = np.where(trend == 1, zlema, np.nan)
    bear = np.where(trend == -1, zlema, np.nan)
    upper_plot = np.where(trend == -1, upper, np.nan)
    lower_plot = np.where(trend == 1, lower, np.nan)
    previous = np.concatenate(([0], trend[:-1]))
    bull_flip, bear_flip = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    buys, sells = np.zeros(len(df), dtype=bool), np.zeros(len(df), dtype=bool)
    for index in range(1, len(df)):
        if trend[index] == trend[index - 1] == 1 and np.isfinite(zlema[index]) and np.isfinite(zlema[index - 1]):
            buys[index] = closes[index - 1] <= zlema[index - 1] and closes[index] > zlema[index]
        elif trend[index] == trend[index - 1] == -1 and np.isfinite(zlema[index]) and np.isfinite(zlema[index - 1]):
            sells[index] = closes[index - 1] >= zlema[index - 1] and closes[index] < zlema[index]
    lows, highs = low.to_numpy(), high.to_numpy()
    return {**_output("Zero Lag Trend Signals", [_line("zero_lag_bull", "Zero Lag Bull", bull, overlay=True, color="#00ffbb"), _line("zero_lag_bear", "Zero Lag Bear", bear, overlay=True, color="#ff1100"), _line("zero_lag_upper", "Upper Band", upper_plot, overlay=True, color="#ff5252"), _line("zero_lag_lower", "Lower Band", lower_plot, overlay=True, color="#00e676")]), "signals": [
        {"type": "buy", "text": "Long", "data": [float(lows[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00e676"},
        {"type": "sell", "text": "Short", "data": [float(highs[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
        {"type": "sell", "text": "Bear", "data": [float(highs[index]) * 1.015 if bear_flip[index] else None for index in range(len(df))], "color": "#ff1744"},
        {"type": "buy", "text": "Bull", "data": [float(lows[index]) * 0.985 if bull_flip[index] else None for index in range(len(df))], "color": "#00c853"},
    ]}


def _super_bollinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "prd", 12, minimum=2, maximum=200)
    multiplier = _number(params, "mult", 2, minimum=0.1, maximum=10)
    show_zigzag = bool(params.get("show_zigzag", True))
    signal_mode = str(params.get("signal", "Signal")).lower()
    deviation_mode = str(params.get("dev", "ZigZag")).lower()
    show_tp = bool(params.get("show_tp", False))
    tp_type = str(params.get("tp_type", "Median")).lower()
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    basis = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper, lower = basis + multiplier * std, basis - multiplier * std
    closes = close.to_numpy()
    trend, sbt = np.zeros(len(df), dtype=int), np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(closes[index]) or not np.isfinite(upper.iloc[index]) or not np.isfinite(lower.iloc[index]):
            if index:
                trend[index], sbt[index] = trend[index - 1], sbt[index - 1]
            continue
        trend[index] = 1 if closes[index] > upper.iloc[index] else -1 if closes[index] < lower.iloc[index] else trend[index - 1]
        sbt[index] = lower.iloc[index] if trend[index] > 0 else upper.iloc[index] if trend[index] < 0 else basis.iloc[index]
    previous = np.concatenate(([0], trend[:-1]))
    sbt_up, sbt_down = np.where(trend > 0, sbt, np.nan), np.where(trend < 0, sbt, np.nan)
    zigzag = np.full(len(df), np.nan)
    last_turn = np.nan
    for index in range(len(df)):
        if trend[index] != 0 and trend[index] != previous[index]:
            last_turn = closes[index]
        if np.isfinite(last_turn):
            zigzag[index] = last_turn
    zigzag_diff = np.concatenate(([np.nan], np.diff(zigzag)))
    trend_buy, trend_sell = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    buys = (closes > upper.to_numpy()) & (previous <= 0) if deviation_mode == "bollinger" else trend_buy
    sells = (closes < lower.to_numpy()) & (previous >= 0) if deviation_mode == "bollinger" else trend_sell
    if signal_mode == "zigzag":
        buys, sells = trend_buy & (zigzag_diff > 0), trend_sell & (zigzag_diff < 0)
    plots = [_line("sbt_up", "SBT Up", sbt_up, overlay=True, color="#00bcd4"), _line("sbt_down", "SBT Down", sbt_down, overlay=True, color="#ff5252")]
    if show_zigzag:
        plots.append(_line("sbt_zigzag", "ZigZag", zigzag, overlay=True, color="#9e9e9e"))
    if show_tp:
        plots.append(_line("sbt_take_profit", "Take Profit", basis if tp_type == "basis" else (upper + lower) / 2, overlay=True, color="#ff9800"))
    return {**_output("SuperBollingerTrend", plots), "signals": [
        {"type": "buy", "text": "Buy", "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))], "color": "#00c853"},
        {"type": "sell", "text": "Sell", "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))], "color": "#ff5252"},
    ]}


def _obv(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    close, volume = _close(df), _series(df, "volume").fillna(0)
    direction = np.sign(close.diff()).fillna(0)
    values = (direction * volume).cumsum()
    if len(values):
        values.iloc[0] = volume.iloc[0]
    return _output("OBV", [_line("obv", "OBV", values)])


def _ad(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0)
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    return _output("AD", [_line("ad", "AD", (clv.fillna(0) * volume).cumsum())])


def _adosc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast", 3)
    slow = _integer(params, "slow", 10, minimum=2)
    if fast >= slow:
        raise ValueError("invalid parameter: fast")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0)
    ad = ((((close - low) - (high - close)) / (high - low).replace(0, np.nan)).fillna(0) * volume).cumsum()
    return _output("ADOSC", [_line("adosc", f"ADOSC({fast},{slow})", _ema(ad, fast) - _ema(ad, slow))])


def _kdj(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 9)
    k_period = _integer(params, "k", 3)
    d_period = _integer(params, "d", 3)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    rsv = ((close - lowest) / (highest - lowest).replace(0, np.nan) * 100).fillna(50)
    k = pd.Series(np.nan, index=df.index, dtype=float)
    d = pd.Series(np.nan, index=df.index, dtype=float)
    k_prev, d_prev = 50.0, 50.0
    for index in range(len(df)):
        if index < period - 1:
            continue
        k_prev = ((k_period - 1) * k_prev + rsv.iloc[index]) / k_period
        d_prev = ((d_period - 1) * d_prev + k_prev) / d_period
        k.iloc[index], d.iloc[index] = k_prev, d_prev
    return _output("KDJ", [
        _line("k", f"K({period},{k_period})", k),
        _line("d", f"D({d_period})", d, color="#4ECDC4"),
        _line("j", "J", 3 * k - 2 * d, color="#95E1D3"),
    ])


def _vwap(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    volume = _series(df, "volume").fillna(0)
    denom = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    values = (typical * volume).rolling(period, min_periods=period).sum() / denom
    return _output("Volume Weighted Average Price", [_line("vwap", f"VWAP({period})", values, overlay=True)])


def _roc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    values = _close(df).pct_change(periods=period) * 100
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Rate of Change", [_line("roc", f"ROC({period})", values)])


def _momentum(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    values = _close(df).diff(period)
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Momentum", [_line("mtm", f"MTM({period})", values)])


def _bias(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    close = _close(df)
    plots = []
    for key, default_period in (("short", 6), ("medium", 12), ("long", 24)):
        period = _integer(params, key, default_period)
        plots.append(_line(key, f"BIAS {key}({period})", (close / close.rolling(period, min_periods=period).mean() - 1) * 100))
    return _output("Bias Ratio", plots)


def _trix(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    close = _close(df)
    first = _ema(close, period)
    second = _ema(first, period)
    third = _ema(second, period)
    values = third.pct_change() * 100
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Triple Exponential Average", [_line("trix", f"TRIX({period})", values)])


def _sar_rate(params: Mapping[str, Any], key: str, default_percent: float) -> float:
    value = _number(params, key, default_percent, minimum=0.000001, maximum=100)
    return value / 100 if value > 1 else value


def _sar(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    # Preserve the existing frontend public defaults (2/2/20) while computing
    # with decimal SAR acceleration values (0.02/0.02/0.2).
    step = _sar_rate(params, "step", 2)
    maximum = _sar_rate(params, "max", 20)
    if maximum < step:
        raise ValueError("invalid parameter: max")
    high = _series(df, "high").to_numpy(dtype=float, copy=False)
    low = _series(df, "low").to_numpy(dtype=float, copy=False)
    values = np.full(len(df), np.nan)
    if len(df):
        rising, af, extreme, sar = True, step, high[0], low[0]
        values[0] = sar
        for index in range(1, len(df)):
            sar = sar + af * (extreme - sar)
            if rising:
                sar = min(sar, low[index - 1], low[index - 2] if index > 1 else low[index - 1])
                if low[index] < sar:
                    rising, sar, extreme, af = False, extreme, low[index], step
                elif high[index] > extreme:
                    extreme, af = high[index], min(maximum, af + step)
            else:
                sar = max(sar, high[index - 1], high[index - 2] if index > 1 else high[index - 1])
                if high[index] > sar:
                    rising, sar, extreme, af = True, extreme, high[index], step
                elif low[index] < extreme:
                    extreme, af = low[index], min(maximum, af + step)
            values[index] = sar
    return _output("Parabolic SAR", [_line("sar", "SAR", values, overlay=True)])


def _supertrend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2)
    multiplier = _number(params, "multiplier", 3.0, minimum=0.1, maximum=10)
    atr = _atr(df, period)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    hl2 = (high + low) / 2
    upper, lower = hl2 + multiplier * atr, hl2 - multiplier * atr
    final_upper = pd.Series(np.nan, index=df.index)
    final_lower = pd.Series(np.nan, index=df.index)
    line = pd.Series(np.nan, index=df.index)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if index < period - 1 or not np.isfinite(upper.iloc[index]) or not np.isfinite(lower.iloc[index]):
            continue
        if index == period - 1 or direction[index - 1] == 0:
            final_upper.iloc[index], final_lower.iloc[index] = upper.iloc[index], lower.iloc[index]
            direction[index] = 1 if close.iloc[index] >= hl2.iloc[index] else -1
        else:
            final_upper.iloc[index] = upper.iloc[index] if upper.iloc[index] < final_upper.iloc[index - 1] or close.iloc[index - 1] > final_upper.iloc[index - 1] else final_upper.iloc[index - 1]
            final_lower.iloc[index] = lower.iloc[index] if lower.iloc[index] > final_lower.iloc[index - 1] or close.iloc[index - 1] < final_lower.iloc[index - 1] else final_lower.iloc[index - 1]
            direction[index] = 1 if close.iloc[index] > final_upper.iloc[index - 1] else -1 if close.iloc[index] < final_lower.iloc[index - 1] else direction[index - 1]
        line.iloc[index] = final_lower.iloc[index] if direction[index] == 1 else final_upper.iloc[index]
    previous = np.concatenate(([0], direction[:-1]))
    buy = np.where((direction == 1) & (previous == -1), low * 0.995, np.nan)
    sell = np.where((direction == -1) & (previous == 1), high * 1.005, np.nan)
    return {
        "name": "SuperTrend",
        "plots": [
            _line("supertrend_up", "SuperTrend Up", np.where(direction == 1, line, np.nan), overlay=True, color="#00E676"),
            _line("supertrend_down", "SuperTrend Down", np.where(direction == -1, line, np.nan), overlay=True, color="#FF5252"),
        ],
        "signals": [
            {"type": "buy", "text": "L", "data": _clean(buy), "color": "#00E676"},
            {"type": "sell", "text": "S", "data": _clean(sell), "color": "#FF5252"},
        ],
        "layers": [],
    }


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


def _make_definitions() -> dict[str, ChartIndicatorDefinition]:
    defs = [
        ChartIndicatorDefinition("sma", "SMA", "SMA", "line", {"length": 20}, _period_schema(maximum=300), _sma),
        ChartIndicatorDefinition("ema", "EMA", "EMA", "line", {"length": 20}, _period_schema(maximum=300), _ema_indicator),
        ChartIndicatorDefinition("rsi", "RSI", "RSI", "line", {"length": 14}, _period_schema(maximum=200), _rsi),
        ChartIndicatorDefinition("macd", "MACD", "MACD", "macd", {"fast": 12, "slow": 26, "signal": 9}, [
            {"key": "fast", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "slow", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "signal", "labelKey": "indicatorIde.editor.signalLine", "type": "number", "min": 1, "max": 100, "step": 1},
        ], _macd),
        ChartIndicatorDefinition("bb", "Bollinger Bands", "BB", "band", {"length": 20, "mult": 2}, _period_schema(maximum=300) + [
            {"key": "mult", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
        ], _bollinger),
        ChartIndicatorDefinition("atr", "ATR", "ATR", "line", {"period": 14}, _period_schema("period", maximum=200), _atr_indicator),
        ChartIndicatorDefinition("cci", "CCI", "CCI", "line", {"length": 20}, _period_schema(maximum=200), _cci),
        ChartIndicatorDefinition("williams", "Williams %R", "W%R", "line", {"length": 14}, _period_schema(maximum=200), _williams),
        ChartIndicatorDefinition("mfi", "MFI", "MFI", "line", {"length": 14}, _period_schema(maximum=200), _mfi),
        ChartIndicatorDefinition("adx", "ADX", "ADX", "adx", {"length": 14}, _period_schema(maximum=200), _adx),
        ChartIndicatorDefinition("obv", "OBV", "OBV", "line", {}, [], _obv),
        ChartIndicatorDefinition("adosc", "ADOSC", "ADOSC", "line", {"fast": 3, "slow": 10}, [
            {"key": "fast", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "slow", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _adosc),
        ChartIndicatorDefinition("ad", "AD", "AD", "line", {}, [], _ad),
        ChartIndicatorDefinition("kdj", "KDJ", "KDJ", "line", {"period": 9, "k": 3, "d": 3}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "k", "labelKey": "indicatorIde.editor.kSmoothing", "type": "number", "min": 1, "max": 20, "step": 1},
            {"key": "d", "labelKey": "indicatorIde.editor.dSmoothing", "type": "number", "min": 1, "max": 20, "step": 1},
        ], _kdj),
        ChartIndicatorDefinition("vwap", "Volume Weighted Average Price", "VWAP", "line", {"period": 20}, _period_schema("period"), _vwap),
        ChartIndicatorDefinition("sar", "Parabolic SAR", "SAR", "native", {"start": 2, "step": 2, "max": 20}, [
            _number_schema("start", 0.1, 20, 0.1, precision=1, label_key="indicatorIde.editor.sarStart"),
            _number_schema("step", 0.1, 20, 0.1, precision=1, label_key="indicatorIde.editor.sarStep"),
            _number_schema("max", 1, 100, 1, label_key="indicatorIde.editor.sarMaximum"),
        ], _sar, True),
        ChartIndicatorDefinition("roc", "Rate of Change", "ROC", "native", {"period": 12, "smoothing": 6}, _period_schema("period", maximum=300) + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")], _roc, True),
        ChartIndicatorDefinition("mtm", "Momentum", "MTM", "native", {"period": 12, "smoothing": 6}, _period_schema("period", maximum=300) + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")], _momentum, True),
        ChartIndicatorDefinition("bias", "Bias Ratio", "BIAS", "native", {"short": 6, "medium": 12, "long": 24}, [
            _number_schema("short", 1, 100, 1, label_key="indicatorIde.editor.shortPeriod"),
            _number_schema("medium", 2, 200, 1, label_key="indicatorIde.editor.mediumPeriod"),
            _number_schema("long", 3, 500, 1, label_key="indicatorIde.editor.longPeriod"),
        ], _bias, True),
        ChartIndicatorDefinition("trix", "Triple Exponential Average", "TRIX", "native", {"period": 12, "smoothing": 9}, _period_schema("period", maximum=300) + [_number_schema("smoothing", 1, 100, 1, label_key="indicatorIde.editor.smoothing")], _trix, True),
        ChartIndicatorDefinition("supertrend", "SuperTrend", "SuperTrend", "line", {"period": 10, "multiplier": 3.0}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
        ], _supertrend),
        ChartIndicatorDefinition("aroon", "Aroon Oscillator", "Aroon", "line", {"period": 25}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _aroon),
        ChartIndicatorDefinition("stochastic", "Stochastic Oscillator", "Stoch", "line", {"length": 14, "smooth_k": 3, "smooth_d": 3}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "smooth_k", "labelKey": "indicatorIde.editor.kSmoothing", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "smooth_d", "labelKey": "indicatorIde.editor.dSmoothing", "type": "number", "min": 1, "max": 50, "step": 1},
        ], _stochastic),
        ChartIndicatorDefinition("stochastic_rsi", "Stochastic RSI", "Stoch RSI", "line", {"rsi_period": 14, "stochastic_period": 14, "k_period": 3, "d_period": 3}, [
            {"key": "rsi_period", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "stochastic_period", "labelKey": "indicatorIde.editor.stochasticPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "k_period", "labelKey": "indicatorIde.editor.kPeriod", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "d_period", "labelKey": "indicatorIde.editor.dPeriod", "type": "number", "min": 1, "max": 50, "step": 1},
        ], _stochastic_rsi),
        ChartIndicatorDefinition("donchian", "Donchian Channel", "Donchian", "band", {"length": 20}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _donchian),
        ChartIndicatorDefinition("keltner", "Keltner Channel", "Keltner", "band", {"period": 20, "atr_period": 10, "multiplier": 2.0}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 8, "step": 0.25, "precision": 2},
        ], _keltner),
        ChartIndicatorDefinition("ichimoku", "Ichimoku Cloud", "Ichimoku", "band", {"conversion_period": 9, "base_period": 26, "span_b_period": 52}, [
            {"key": "conversion_period", "labelKey": "indicatorIde.editor.conversionPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "base_period", "labelKey": "indicatorIde.editor.basePeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "span_b_period", "labelKey": "indicatorIde.editor.spanBPeriod", "type": "number", "min": 2, "max": 300, "step": 1},
        ], _ichimoku),
        ChartIndicatorDefinition("cmf", "Chaikin Money Flow", "CMF", "line", {"period": 20}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _cmf),
        ChartIndicatorDefinition("cmo", "Chande Momentum Oscillator", "CMO", "line", {"period": 14}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _cmo),
        ChartIndicatorDefinition("dema", "Double Exponential Moving Average", "DEMA", "line", {"period": 20}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 300, "step": 1},
        ], _dema),
        ChartIndicatorDefinition("hma", "Hull Moving Average", "HMA", "line", {"period": 20}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 300, "step": 1},
        ], _hma),
        ChartIndicatorDefinition("vortex", "Vortex Indicator", "Vortex", "line", {"period": 14}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _vortex),
        ChartIndicatorDefinition("ultimate_oscillator", "Ultimate Oscillator", "UO", "line", {"short_period": 7, "medium_period": 14, "long_period": 28}, [
            {"key": "short_period", "labelKey": "indicatorIde.editor.shortPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "medium_period", "labelKey": "indicatorIde.editor.mediumPeriod", "type": "number", "min": 3, "max": 150, "step": 1},
            {"key": "long_period", "labelKey": "indicatorIde.editor.longPeriod", "type": "number", "min": 4, "max": 250, "step": 1},
        ], _ultimate_oscillator),
        ChartIndicatorDefinition("fisher", "Fisher Transform", "Fisher", "line", {"period": 10, "signal_period": 1}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 1, "max": 50, "step": 1},
        ], _fisher),
        ChartIndicatorDefinition("force_index", "Force Index", "Force", "line", {"period": 13}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 1, "max": 200, "step": 1},
        ], _force_index),
        ChartIndicatorDefinition("ease_of_movement", "Ease of Movement", "EOM", "line", {"period": 14, "volume_divisor": 10000.0}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "volume_divisor", "labelKey": "indicatorIde.editor.volumeDivisor", "type": "number", "min": 1, "max": 1_000_000_000, "step": 1000, "precision": 0},
        ], _ease_of_movement),
        ChartIndicatorDefinition("chaikin_oscillator", "Chaikin Oscillator", "Chaikin", "line", {"fast_period": 3, "slow_period": 10}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _chaikin_oscillator),
        ChartIndicatorDefinition("volume_oscillator", "Volume Oscillator", "Volume Osc", "line", {"fast_period": 5, "slow_period": 20, "signal_period": 5}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 1, "max": 100, "step": 1},
        ], _volume_oscillator),
        ChartIndicatorDefinition("pvt", "Price Volume Trend", "PVT", "line", {"signal_period": 21}, [
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 1, "max": 200, "step": 1},
        ], _pvt),
        ChartIndicatorDefinition("rvi", "Relative Vigor Index", "RVI", "line", {"period": 10}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _rvi),
        ChartIndicatorDefinition("choppiness", "Choppiness Index", "CHOP", "line", {"period": 14}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _choppiness),
        ChartIndicatorDefinition("qqe", "QQE Signals", "QQE", "line", {"rsi_period": 14, "rsi_smoothing": 5, "qqe_factor": 4.236}, [
            {"key": "rsi_period", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "rsi_smoothing", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "qqe_factor", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.5, "max": 10, "step": 0.1, "precision": 3},
        ], _qqe),
        ChartIndicatorDefinition("rmi_trend", "RMI Trend Sniper", "RMI Trend", "line", {"length": 14, "pmom": 66, "nmom": 30}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "pmom", "labelKey": "indicatorIde.editor.positiveThreshold", "type": "number", "min": 50, "max": 100, "step": 1},
            {"key": "nmom", "labelKey": "indicatorIde.editor.negativeThreshold", "type": "number", "min": 0, "max": 50, "step": 1},
        ], _rmi),
        ChartIndicatorDefinition("stc", "Schaff Trend Cycle", "STC", "line", {"fast_period": 23, "slow_period": 50, "cycle_period": 10, "smoothing": 0.5}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 150, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 250, "step": 1},
            {"key": "cycle_period", "labelKey": "indicatorIde.editor.cyclePeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "smoothing", "labelKey": "indicatorIde.editor.smoothingFactor", "type": "number", "min": 0.1, "max": 1, "step": 0.1, "precision": 1},
        ], _stc),
        ChartIndicatorDefinition("tsi", "True Strength Index", "TSI", "line", {"long_period": 25, "short_period": 13, "signal_period": 7}, [
            {"key": "long_period", "labelKey": "indicatorIde.editor.longPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "short_period", "labelKey": "indicatorIde.editor.shortPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _tsi),
        ChartIndicatorDefinition("connors_rsi", "Connors RSI", "CRSI", "line", {"rsi_period": 3, "streak_rsi_period": 2, "rank_period": 100}, [
            {"key": "rsi_period", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "streak_rsi_period", "labelKey": "indicatorIde.editor.streakRsiPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "rank_period", "labelKey": "indicatorIde.editor.rankPeriod", "type": "number", "min": 5, "max": 200, "step": 1},
        ], _connors_rsi),
        ChartIndicatorDefinition("coppock", "Coppock Curve", "Coppock", "line", {"long_roc": 14, "short_roc": 11, "wma_period": 10}, [
            {"key": "long_roc", "labelKey": "indicatorIde.editor.longPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "short_roc", "labelKey": "indicatorIde.editor.shortPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "wma_period", "labelKey": "indicatorIde.editor.wmaPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _coppock),
        ChartIndicatorDefinition("dpo", "Detrended Price Oscillator", "DPO", "line", {"period": 20}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _dpo),
        ChartIndicatorDefinition("mass_index", "Mass Index", "Mass", "line", {"ema_period": 9, "sum_period": 25}, [
            {"key": "ema_period", "labelKey": "indicatorIde.editor.emaPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "sum_period", "labelKey": "indicatorIde.editor.sumPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _mass_index),
        ChartIndicatorDefinition("ulcer_index", "Ulcer Index", "Ulcer", "line", {"period": 14}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _ulcer_index),
        ChartIndicatorDefinition("klinger", "Klinger Volume Oscillator", "KVO", "line", {"fast_period": 34, "slow_period": 55, "signal_period": 13}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 250, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _klinger),
        ChartIndicatorDefinition("ppo", "Percentage Price Oscillator", "PPO", "line", {"fast_period": 12, "slow_period": 26, "signal_period": 9}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _ppo),
        ChartIndicatorDefinition("volume_macd", "Volume Weighted MACD", "VW MACD", "line", {"fast_length": 12, "slow_length": 26, "signal_length": 9, "histogram": True}, [
            {"key": "fast_length", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "slow_length", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_length", "labelKey": "indicatorIde.editor.signalLine", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "histogram", "labelKey": "indicatorIde.editor.showHistogram", "type": "bool"},
        ], _volume_macd),
        ChartIndicatorDefinition("bop", "Balance of Power", "BOP", "line", {"smooth_period": 1}, [
            {"key": "smooth_period", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 1, "max": 100, "step": 1},
        ], _bop),
        ChartIndicatorDefinition("relative_volatility", "Relative Volatility Index", "RVI", "line", {"period": 14}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _rvi_volatility),
        ChartIndicatorDefinition("elder_ray", "Elder Ray Index", "Elder Ray", "line", {"period": 13}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _elder_ray),
        ChartIndicatorDefinition("kama", "Kaufman Adaptive Moving Average", "KAMA", "line", {"period": 10, "fast_period": 2, "slow_period": 30}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 2, "max": 200, "step": 1},
        ], _kama),
        ChartIndicatorDefinition("vidya", "Variable Moving Average", "VIDYA", "line", {"period": 20, "momentum_period": 9, "signal_period": 9}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "momentum_period", "labelKey": "indicatorIde.editor.momentumPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], _vidya),
        ChartIndicatorDefinition("half_trend", "HalfTrend", "HalfTrend", "band", {"amplitude": 2, "atr_period": 100, "channel_deviation": 2.0}, [
            {"key": "amplitude", "labelKey": "indicatorIde.editor.amplitude", "type": "number", "min": 1, "max": 30, "step": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "channel_deviation", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 6, "step": 0.25, "precision": 2},
        ], _half_trend),
        ChartIndicatorDefinition("gaussian_trend", "Gaussian Filter Trend", "Gaussian", "band", {"period": 20, "poles": 3, "atr_period": 14, "multiplier": 1.5}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "poles", "labelKey": "indicatorIde.editor.poles", "type": "number", "min": 1, "max": 6, "step": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 8, "step": 0.25, "precision": 2},
        ], _gaussian_trend),
        ChartIndicatorDefinition("atr_trailing_stop", "ATR Trailing Stop", "ATR Stop", "band", {"atr_length": 14, "atr_multiplier": 3.0, "source": "close"}, [
            {"key": "atr_length", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "atr_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.5, "max": 8, "step": 0.1, "precision": 1},
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2"]},
        ], _atr_trailing_stop),
        ChartIndicatorDefinition("chandelier_exit", "Chandelier Exit", "Chandelier", "line", {"length": 22, "atr_multiplier": 3.0}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 5, "max": 100, "step": 1},
            {"key": "atr_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 1, "max": 6, "step": 0.25, "precision": 2},
        ], _chandelier),
        ChartIndicatorDefinition("atr_rope", "ATR Rope", "ATR Rope", "line", {"atr_period": 14, "multiplier": 1.5}, [
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 8, "step": 0.25, "precision": 2},
        ], _atr_rope),
        ChartIndicatorDefinition("pmax", "PMax Trend Filter", "PMax", "line", {"ma_period": 10, "atr_period": 10, "atr_multiplier": 3.0}, [
            {"key": "ma_period", "labelKey": "indicatorIde.editor.emaPeriod", "type": "number", "min": 5, "max": 60, "step": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 5, "max": 60, "step": 1},
            {"key": "atr_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 1, "max": 6, "step": 0.25, "precision": 2},
        ], _pmax),
        ChartIndicatorDefinition("range_filter", "Range Filter", "Range Filter", "band", {"sampling_period": 50, "range_multiplier": 3.0}, [
            {"key": "sampling_period", "labelKey": "indicatorIde.editor.samplingPeriod", "type": "number", "min": 10, "max": 150, "step": 5},
            {"key": "range_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 1, "max": 6, "step": 0.25, "precision": 2},
        ], _range_filter),
        ChartIndicatorDefinition("vwap_channel", "VWAP Price Channel", "VWAP Channel", "band", {"period": 30, "deviation": 1.5}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 5, "max": 200, "step": 1},
            {"key": "deviation", "labelKey": "indicatorIde.editor.deviation", "type": "number", "min": 0.25, "max": 5, "step": 0.25, "precision": 2},
        ], _vwap_channel),
        ChartIndicatorDefinition("turtle_channels", "Turtle Trade Channels", "Turtle", "band", {"entry_length": 20, "exit_length": 10}, [
            {"key": "entry_length", "labelKey": "indicatorIde.editor.entryPeriod", "type": "number", "min": 5, "max": 100, "step": 1},
            {"key": "exit_length", "labelKey": "indicatorIde.editor.exitPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
        ], _turtle),
        ChartIndicatorDefinition("nrtr", "NRTR", "NRTR", "line", {"percentage": 1.0, "mult": 0.0, "length": 20}, [
            {"key": "percentage", "labelKey": "indicatorIde.editor.percentage", "type": "number", "min": 0.25, "max": 5, "step": 0.25, "precision": 2},
            {"key": "mult", "labelKey": "indicatorIde.editor.volatilityMultiplier", "type": "number", "min": 0, "max": 3, "step": 0.1, "precision": 1},
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 5, "max": 100, "step": 1},
        ], _nrtr),
        ChartIndicatorDefinition("trend_state", "Trend State Signals", "Trend State", "line", {"length": 20, "multiplier": 3.5, "src_type": "close"}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
            {"key": "src_type", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
        ], _trend_state),
        ChartIndicatorDefinition("zero_lag_trend", "Zero Lag Trend Signals", "Zero Lag", "band", {"length": 70, "mult": 1.2}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "mult", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
        ], _zero_lag_trend),
        ChartIndicatorDefinition("super_bollinger", "Super Bollinger Trend", "SBT", "band", {"prd": 12, "mult": 2.0, "show_zigzag": True, "signal": "Signal", "dev": "ZigZag", "show_tp": False, "tp_type": "Median"}, [
            {"key": "prd", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "mult", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
            {"key": "show_zigzag", "labelKey": "indicatorIde.editor.showZigzag", "type": "bool"},
            {"key": "signal", "labelKey": "indicatorIde.editor.signalMode", "type": "string", "options": ["Signal", "ZigZag"]},
            {"key": "dev", "labelKey": "indicatorIde.editor.deviationMode", "type": "string", "options": ["ZigZag", "Bollinger"]},
            {"key": "show_tp", "labelKey": "indicatorIde.editor.showTakeProfit", "type": "bool"},
            {"key": "tp_type", "labelKey": "indicatorIde.editor.takeProfitType", "type": "string", "options": ["Median", "Basis"]},
        ], _super_bollinger),
        ChartIndicatorDefinition("alpha_trend", "AlphaTrend", "AlphaTrend", "line", {"atr_period": 14, "momentum_period": 14, "multiplier": 1.0, "confirmation_lag": 2}, [
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "momentum_period", "labelKey": "indicatorIde.editor.momentumPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 8, "step": 0.25},
            {"key": "confirmation_lag", "labelKey": "indicatorIde.editor.confirmationLag", "type": "number", "min": 1, "max": 10, "step": 1},
        ], None),
        ChartIndicatorDefinition("optimized_trend_tracker", "Optimized Trend Tracker", "OTT", "line", {"length": 2, "var_length": 9, "percent": 1.4, "base": 200}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "var_length", "labelKey": "indicatorIde.editor.varLength", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "percent", "labelKey": "indicatorIde.editor.percentage", "type": "number", "min": 0.1, "max": 10, "step": 0.1},
            {"key": "base", "labelKey": "indicatorIde.editor.ottBase", "type": "number", "min": 10, "max": 1000, "step": 10},
        ], None),
        ChartIndicatorDefinition("std_filtered_gaussian", "STD-Filtered N-Pole Gaussian Filter", "STD Gaussian", "line", {"period": 25, "poles": 5, "filter_period": 10, "filter_strength": 1.0}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "poles", "labelKey": "indicatorIde.editor.poles", "type": "number", "min": 1, "max": 6, "step": 1},
            {"key": "filter_period", "labelKey": "indicatorIde.editor.filterPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "filter_strength", "labelKey": "indicatorIde.editor.filterStrength", "type": "number", "min": 0, "max": 5, "step": 0.25},
        ], None),
        ChartIndicatorDefinition("adaptive_trend_filter", "Adaptive Trend Filter", "Adaptive Filter", "band", {"alpha_filter": 0.01, "beta_filter": 0.1, "filter_period": 21, "supertrend_factor": 1.0, "atr_period": 7}, [
            {"key": "alpha_filter", "labelKey": "indicatorIde.editor.alphaFilter", "type": "number", "min": 0.001, "max": 1, "step": 0.001},
            {"key": "beta_filter", "labelKey": "indicatorIde.editor.betaFilter", "type": "number", "min": 0.001, "max": 2, "step": 0.001},
            {"key": "filter_period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "supertrend_factor", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 8, "step": 0.25},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("vegas_supertrend", "Multi-Step Vegas SuperTrend", "Vegas ST", "band", {"atr_period": 10, "vegas_period": 100, "supertrend_multiplier": 5.0, "volatility_adjustment": 5.0}, [
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "vegas_period", "labelKey": "indicatorIde.editor.vegasPeriod", "type": "number", "min": 5, "max": 300, "step": 1},
            {"key": "supertrend_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.5, "max": 12, "step": 0.5},
            {"key": "volatility_adjustment", "labelKey": "indicatorIde.editor.volatilityAdjustment", "type": "number", "min": 0, "max": 20, "step": 0.5},
        ], None),
        ChartIndicatorDefinition("dsav", "DSAV Dynamic Swing Anchored VWAP", "DSAV", "line", {"prd": 50, "base_apt": 20, "use_adapt": False, "vol_bias": 10.0}, [
            {"key": "prd", "labelKey": "indicatorIde.editor.swingPeriod", "type": "number", "min": 5, "max": 200, "step": 1},
            {"key": "base_apt", "labelKey": "indicatorIde.editor.halfLife", "type": "number", "min": 5, "max": 300, "step": 1},
            {"key": "use_adapt", "labelKey": "indicatorIde.editor.useAdaptive", "type": "bool"},
            {"key": "vol_bias", "labelKey": "indicatorIde.editor.volatilityBias", "type": "number", "min": 0, "max": 20, "step": 0.5},
        ], None),
        ChartIndicatorDefinition("lowess", "LOWESS Smoothing", "LOWESS", "band", {"length": 100, "malen": 100}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 10, "max": 200, "step": 1},
            {"key": "malen", "labelKey": "indicatorIde.editor.lowessPeriod", "type": "number", "min": 5, "max": 200, "step": 1},
        ], None),
        ChartIndicatorDefinition("price_radio", "John Ehlers The Price Radio", "Price Radio", "line", {"am_period": 8, "fm_period": 30, "fm_gain": 10.0}, [
            {"key": "am_period", "labelKey": "indicatorIde.editor.amPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "fm_period", "labelKey": "indicatorIde.editor.fmPeriod", "type": "number", "min": 3, "max": 100, "step": 1},
            {"key": "fm_gain", "labelKey": "indicatorIde.editor.fmGain", "type": "number", "min": 0.1, "max": 100, "step": 0.1},
        ], None),
        ChartIndicatorDefinition("adaptive_trend_trail", "Adaptive Trend Trail", "ATT", "band", {"trend_length": 34, "momentum_length": 12, "sensitivity": 0.35, "st_fast_length": 9, "st_fast_factor": 1.45, "st_mid_length": 14, "st_mid_factor": 1.95, "st_slow_length": 21, "st_slow_factor": 2.55, "trail_size": 1.0, "smoothness": 5, "overlay_mode": "Trail"}, [
            {"key": "trend_length", "labelKey": "indicatorIde.editor.trendPeriod", "type": "number", "min": 5, "max": 200, "step": 1},
            {"key": "momentum_length", "labelKey": "indicatorIde.editor.momentumPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "sensitivity", "labelKey": "indicatorIde.editor.sensitivity", "type": "number", "min": 0, "max": 1, "step": 0.05},
            {"key": "st_fast_length", "labelKey": "indicatorIde.editor.fastAtrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "st_fast_factor", "labelKey": "indicatorIde.editor.fastAtrFactor", "type": "number", "min": 0.5, "max": 5, "step": 0.05},
            {"key": "st_mid_length", "labelKey": "indicatorIde.editor.midAtrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "st_mid_factor", "labelKey": "indicatorIde.editor.midAtrFactor", "type": "number", "min": 0.5, "max": 6, "step": 0.05},
            {"key": "st_slow_length", "labelKey": "indicatorIde.editor.slowAtrPeriod", "type": "number", "min": 2, "max": 150, "step": 1},
            {"key": "st_slow_factor", "labelKey": "indicatorIde.editor.slowAtrFactor", "type": "number", "min": 0.5, "max": 8, "step": 0.05},
            {"key": "trail_size", "labelKey": "indicatorIde.editor.trailSize", "type": "number", "min": 0.5, "max": 2, "step": 0.05},
            {"key": "smoothness", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "overlay_mode", "labelKey": "indicatorIde.editor.overlayMode", "type": "string", "options": ["Trail", "Bands", "None"]},
        ], None),
        ChartIndicatorDefinition("spma_trend_nal", "SPMA Trend NAL", "SPMA", "band", {"source": "close", "baseline_length": 30, "percentrank_lookback": 30, "percentile_gate": 50.0, "use_asym_bands": False, "vol_method": "MeanAD", "vol_length": 14, "vol_multiple": 0.75, "quantile_pct": 90.0, "use_slope_gate": False, "slope_length": 10, "slope_gate": 0.5}, [
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "baseline_length", "labelKey": "indicatorIde.editor.basePeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "percentrank_lookback", "labelKey": "indicatorIde.editor.percentRankPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "percentile_gate", "labelKey": "indicatorIde.editor.percentileGate", "type": "number", "min": 0, "max": 99, "step": 1},
            {"key": "use_asym_bands", "labelKey": "indicatorIde.editor.useAsymmetricBands", "type": "bool"},
            {"key": "vol_length", "labelKey": "indicatorIde.editor.volatilityPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "vol_multiple", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.05, "max": 8, "step": 0.05},
            {"key": "quantile_pct", "labelKey": "indicatorIde.editor.quantilePercentile", "type": "number", "min": 50, "max": 99, "step": 1},
            {"key": "use_slope_gate", "labelKey": "indicatorIde.editor.useSlopeGate", "type": "bool"},
            {"key": "slope_length", "labelKey": "indicatorIde.editor.slopePeriod", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "slope_gate", "labelKey": "indicatorIde.editor.slopeGate", "type": "number", "min": -20, "max": 20, "step": 0.1},
            {"key": "vol_method", "labelKey": "indicatorIde.editor.volatilityMethod", "type": "string", "options": ["SD", "ATR", "MeanAD", "MedianAD", "Quantile"]},
        ], None),
        ChartIndicatorDefinition("powertrend_volume_range_filter", "PowerTrend Volume Range Filter", "PowerTrend", "band", {"range_period": 34, "range_multiplier": 2.5, "fast_period": 21, "slow_period": 55, "volume_period": 34, "min_relative_volume": 1.05}, [
            {"key": "range_period", "labelKey": "indicatorIde.editor.rangePeriod", "type": "number", "min": 10, "max": 120, "step": 2},
            {"key": "range_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 1, "max": 6, "step": 0.25, "precision": 2},
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 5, "max": 60, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 20, "max": 160, "step": 5},
            {"key": "volume_period", "labelKey": "indicatorIde.editor.volumePeriod", "type": "number", "min": 10, "max": 120, "step": 2},
            {"key": "min_relative_volume", "labelKey": "indicatorIde.editor.minRelativeVolume", "type": "number", "min": 0.5, "max": 3, "step": 0.05, "precision": 2},
        ], None),
        ChartIndicatorDefinition("g_channels", "G Channels", "G Channels", "band", {"length": 100, "signal_mode": "close"}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 20, "max": 240, "step": 5},
            {"key": "signal_mode", "labelKey": "indicatorIde.editor.signalMode", "type": "string", "options": ["close", "channel"]},
        ], None),
        ChartIndicatorDefinition("wavetrend_oscillator", "WaveTrend Oscillator", "WaveTrend", "line", {"channel_length": 10, "average_length": 21}, [
            {"key": "channel_length", "labelKey": "indicatorIde.editor.channelPeriod", "type": "number", "min": 3, "max": 40, "step": 1},
            {"key": "average_length", "labelKey": "indicatorIde.editor.averagePeriod", "type": "number", "min": 3, "max": 80, "step": 1},
        ], None),
        ChartIndicatorDefinition("nadaraya_watson_envelope", "Nadaraya-Watson Envelope", "NW Envelope", "band", {"lookback": 64, "bandwidth": 8.0, "atr_period": 21, "envelope_multiplier": 2.0}, [
            {"key": "lookback", "labelKey": "indicatorIde.editor.lookback", "type": "number", "min": 20, "max": 160, "step": 4},
            {"key": "bandwidth", "labelKey": "indicatorIde.editor.bandwidth", "type": "number", "min": 2, "max": 30, "step": 0.5, "precision": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 5, "max": 80, "step": 1},
            {"key": "envelope_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.5, "max": 5, "step": 0.25, "precision": 2},
        ], None),
        ChartIndicatorDefinition("dynamic_linear_regression_channel", "Dynamic Linear Regression Channel", "Regression Channel", "band", {"period": 50, "deviation": 2.0}, [
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 5, "max": 200, "step": 1},
            {"key": "deviation", "labelKey": "indicatorIde.editor.deviation", "type": "number", "min": 0.5, "max": 4, "step": 0.25, "precision": 2},
        ], None),
        ChartIndicatorDefinition("ut_bot_alerts", "UT Bot Alerts", "UT Bot", "line", {"atr_period": 10, "key_value": 1.0}, [
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "key_value", "labelKey": "indicatorIde.editor.sensitivity", "type": "number", "min": 0.25, "max": 10, "step": 0.25, "precision": 2},
        ], None),
        ChartIndicatorDefinition("twin_range_filter", "Twin Range Filter", "Twin Range", "line", {"source": "close", "per1": 27, "mult1": 1.6, "per2": 55, "mult2": 2.0}, [
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"]},
            {"key": "per1", "labelKey": "indicatorIde.editor.fastPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "mult1", "labelKey": "indicatorIde.editor.fastMultiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
            {"key": "per2", "labelKey": "indicatorIde.editor.slowPeriod", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "mult2", "labelKey": "indicatorIde.editor.slowMultiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
        ], None),
        ChartIndicatorDefinition("pivot_point_supertrend", "Pivot Point Supertrend", "Pivot ST", "band", {"pivot_period": 2, "atr_period": 10, "multiplier": 3.0}, [
            {"key": "pivot_period", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 1, "max": 20, "step": 1},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 10, "step": 0.25, "precision": 2},
        ], None),
        ChartIndicatorDefinition("delta_rsi_oscillator", "Delta RSI Oscillator", "Delta RSI", "macd", {"fast_period": 7, "slow_period": 21, "signal_period": 5}, [
            {"key": "fast_period", "labelKey": "indicatorIde.editor.fastRsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "slow_period", "labelKey": "indicatorIde.editor.slowRsiPeriod", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("range_filter_signals", "Range Filter B&S Signals", "Range Filter B&S", "band", {"rng_per": 20, "rng_qty": 3.5}, [
            {"key": "rng_per", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 150, "step": 1},
            {"key": "rng_qty", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
        ], None),
        ChartIndicatorDefinition("know_sure_thing", "Know Sure Thing", "KST", "line", {"roc1_period": 10, "roc2_period": 15, "roc3_period": 20, "roc4_period": 30, "signal_period": 9}, [
            {"key": "roc1_period", "labelKey": "indicatorIde.editor.roc1Period", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "roc2_period", "labelKey": "indicatorIde.editor.roc2Period", "type": "number", "min": 2, "max": 150, "step": 1},
            {"key": "roc3_period", "labelKey": "indicatorIde.editor.roc3Period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "roc4_period", "labelKey": "indicatorIde.editor.roc4Period", "type": "number", "min": 2, "max": 250, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("macd_leader", "MACD Leader", "MACD Leader", "line", {"short_length": 12, "long_length": 26, "sig_length": 9, "show_macd": False, "show_macdsignal": False, "src": "close", "ema_seed": "sma"}, [
            {"key": "short_length", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 1, "max": 200, "step": 1},
            {"key": "long_length", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 2, "max": 500, "step": 1},
            {"key": "sig_length", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 1, "max": 200, "step": 1},
            {"key": "show_macd", "labelKey": "indicatorIde.editor.showMacd", "type": "bool"},
            {"key": "show_macdsignal", "labelKey": "indicatorIde.editor.showMacdSignal", "type": "bool"},
            {"key": "src", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "ema_seed", "labelKey": "indicatorIde.editor.emaSeed", "type": "string", "options": ["sma", "first"]},
        ], None),
        ChartIndicatorDefinition("envelope_rsi_signals", "Envelope RSI Signals", "Envelope RSI", "line", {"rsi_length": 14, "envelope_length": 20, "envelope_multiplier": 1.5, "show_envelope": True}, [
            {"key": "rsi_length", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "envelope_length", "labelKey": "indicatorIde.editor.envelopePeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "envelope_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 5, "step": 0.1, "precision": 1},
            {"key": "show_envelope", "labelKey": "indicatorIde.editor.showEnvelope", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("follow_line_indicator", "Follow Line Indicator", "Follow Line", "line", {"bb_period": 21, "bb_deviations": 1.0, "use_atr_filter": True, "atr_period": 5, "hide_labels": False}, [
            {"key": "bb_period", "labelKey": "indicatorIde.editor.bollingerPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "bb_deviations", "labelKey": "indicatorIde.editor.deviation", "type": "number", "min": 0.1, "max": 5, "step": 0.1, "precision": 1},
            {"key": "use_atr_filter", "labelKey": "indicatorIde.editor.useAtrFilter", "type": "bool"},
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "hide_labels", "labelKey": "indicatorIde.editor.hideLabels", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("exhaustion_levels", "Exhaustion Levels", "Exhaustion", "line", {"exhaustion_switch": True, "level_switch": True, "length": 40, "bars": 10, "thickness": 2}, [
            {"key": "exhaustion_switch", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
            {"key": "level_switch", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "bars", "labelKey": "indicatorIde.editor.exhaustionBars", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "thickness", "labelKey": "indicatorIde.editor.lineWidth", "type": "number", "min": 1, "max": 5, "step": 1},
        ], None),
        ChartIndicatorDefinition("hema_trend_levels", "HEMA Trend Levels", "HEMA", "band", {"length": 50, "atr_length": 14, "atr_multiplier": 1.5, "source": "close", "show_levels": True}, [
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "atr_length", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "atr_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "precision": 1},
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "show_levels", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("market_structure_oscillator", "Market Structure Oscillator", "Market Structure", "line", {"structure_length": 20, "signal_length": 5, "volume_length": 20, "show_signal": True}, [
            {"key": "structure_length", "labelKey": "indicatorIde.editor.structurePeriod", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_length", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "volume_length", "labelKey": "indicatorIde.editor.volumePeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "show_signal", "labelKey": "indicatorIde.editor.showSignal", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("adaptive_supertrend", "Adaptive SuperTrend", "Adaptive ST", "band", {"atr_period": 10, "factor": 3.0, "tqi_period": 14, "smooth_period": 3}, [
            {"key": "atr_period", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "factor", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.25, "max": 10, "step": 0.25},
            {"key": "tqi_period", "labelKey": "indicatorIde.editor.tqiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "smooth_period", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 1, "max": 50, "step": 1},
        ], None),
        ChartIndicatorDefinition("elder_impulse_system", "Elder Impulse System", "Elder Impulse", "band", {"ema_length": 13, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}, [
            {"key": "ema_length", "labelKey": "indicatorIde.editor.emaPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "macd_fast", "labelKey": "indicatorIde.editor.fastPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "macd_slow", "labelKey": "indicatorIde.editor.slowPeriod", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "macd_signal", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("swing_failure_pattern", "Swing Failure Pattern", "SFP", "band", {"length": 5, "bullish": True, "bearish": True, "swing_lines": True, "confirm_lines": True, "sfp_labels": True, "bull_color": "#089981", "bear_color": "#f23645", "validation": "None", "percent": 25.0}, [
            {"key": "length", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "bullish", "labelKey": "indicatorIde.editor.showBullish", "type": "bool"},
            {"key": "bearish", "labelKey": "indicatorIde.editor.showBearish", "type": "bool"},
            {"key": "swing_lines", "labelKey": "indicatorIde.editor.showSwingLevels", "type": "bool"},
            {"key": "confirm_lines", "labelKey": "indicatorIde.editor.showConfirmationLevels", "type": "bool"},
            {"key": "sfp_labels", "labelKey": "indicatorIde.editor.showSfpLabels", "type": "bool"},
            {"key": "bull_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
            {"key": "bear_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
            {"key": "validation", "labelKey": "indicatorIde.editor.validationMode", "type": "string"},
            {"key": "percent", "labelKey": "indicatorIde.editor.sweepPenetration", "type": "number", "min": 0, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("breaks_and_retests", "Breaks and Retests", "Break/Retest", "band", {"lookback": 20, "ret_since": 2, "ret_valid": 2, "breakouts": True, "retests": True, "support_color": "#FF0000", "resistance_color": "#089981"}, [
            {"key": "lookback", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "ret_since", "labelKey": "indicatorIde.editor.retestStartBars", "type": "number", "min": 0, "max": 50, "step": 1},
            {"key": "ret_valid", "labelKey": "indicatorIde.editor.retestWindow", "type": "number", "min": 0, "max": 50, "step": 1},
            {"key": "breakouts", "labelKey": "indicatorIde.editor.showBreakouts", "type": "bool"},
            {"key": "retests", "labelKey": "indicatorIde.editor.showRetests", "type": "bool"},
            {"key": "support_color", "labelKey": "indicatorIde.editor.supportColor", "type": "color"},
            {"key": "resistance_color", "labelKey": "indicatorIde.editor.resistanceColor", "type": "color"},
        ], None),
        ChartIndicatorDefinition("false_breakout", "False Breakout", "False Breakout", "band", {"prd": 20, "minperiod": 5, "maxperiod": 5, "ma_type": "None", "length": 10, "aggressive": False}, [
            {"key": "prd", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "minperiod", "labelKey": "indicatorIde.editor.breakoutGap", "type": "number", "min": 1, "max": 200, "step": 1},
            {"key": "maxperiod", "labelKey": "indicatorIde.editor.signalValidity", "type": "number", "min": 0, "max": 200, "step": 1},
            {"key": "ma_type", "labelKey": "indicatorIde.editor.smoothingMethod", "type": "string", "options": ["None", "WMA", "HMA"]},
            {"key": "length", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "aggressive", "labelKey": "indicatorIde.editor.aggressiveSource", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("multi_kernel_regression", "Multi Kernel Regression", "Kernel Regression", "band", {"repaint": True, "kernel": "Laplace", "bandwidth": 14, "source": "close", "deviations": 2.0, "enable": False, "bullish_color": "#54C294", "bearish_color": "#EB3939", "confirm_bars": 10}, [
            {"key": "repaint", "labelKey": "indicatorIde.editor.compatibilityRepaint", "type": "bool"},
            {"key": "kernel", "labelKey": "indicatorIde.editor.kernelType", "type": "string", "options": ["Triangular", "Gaussian", "Epanechnikov", "Logistic", "Log Logistic", "Cosine", "Sinc", "Laplace", "Quartic", "Parabolic", "Exponential", "Silverman", "Cauchy", "Tent", "Wave", "Power", "Morters"]},
            {"key": "bandwidth", "labelKey": "indicatorIde.editor.bandwidth", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "deviations", "labelKey": "indicatorIde.editor.deviation", "type": "number", "min": 0, "max": 10, "step": 0.25},
            {"key": "enable", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
            {"key": "bullish_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
            {"key": "bearish_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
            {"key": "confirm_bars", "labelKey": "indicatorIde.editor.confirmationBars", "type": "number", "min": 1, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("smart_money_breakouts", "Smart Money Breakouts", "SM Breakouts", "band", {"length": 20, "candle_type": "Wicks", "rr_ratio": 1.1, "sl_type": "Close", "show_sl": False, "line_style": "Dashed", "pivot_high_color": "#028545", "pivot_low_color": "#F60707", "tp_color": "#148D9A", "sl_color": "#F60707"}, [
            {"key": "length", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "candle_type", "labelKey": "indicatorIde.editor.breakoutSource", "type": "string", "options": ["Wicks", "Body"]},
            {"key": "rr_ratio", "labelKey": "indicatorIde.editor.rewardRiskRatio", "type": "number", "min": 0.1, "max": 20, "step": 0.1},
            {"key": "sl_type", "labelKey": "indicatorIde.editor.stopTrigger", "type": "string", "options": ["Close", "High/Low"]},
            {"key": "show_sl", "labelKey": "indicatorIde.editor.showStopLine", "type": "bool"},
            {"key": "line_style", "labelKey": "indicatorIde.editor.lineStyle", "type": "string", "options": ["Solid", "Dashed", "Dotted"]},
            {"key": "pivot_high_color", "labelKey": "indicatorIde.editor.pivotHighColor", "type": "color"},
            {"key": "pivot_low_color", "labelKey": "indicatorIde.editor.pivotLowColor", "type": "color"},
            {"key": "tp_color", "labelKey": "indicatorIde.editor.takeProfitColor", "type": "color"},
            {"key": "sl_color", "labelKey": "indicatorIde.editor.stopLossColor", "type": "color"},
        ], None),
        ChartIndicatorDefinition("swing_highs_lows_candle_patterns", "Swing Highs/Lows & Candle Patterns", "Swing Patterns", "band", {"length": 21}, [
            {"key": "length", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 1, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("trendlines_with_breaks", "Trendlines with Breaks", "Trendline Breaks", "band", {"length": 14, "mult": 1.0, "calc_method": "Atr", "unique_signal": False}, [
            {"key": "length", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "mult", "labelKey": "indicatorIde.editor.slopeMultiplier", "type": "number", "min": 0.1, "max": 5.0, "step": 0.1},
            {"key": "calc_method", "labelKey": "indicatorIde.editor.slopeMethod", "type": "string", "options": ["Atr", "Stdev", "Linreg"]},
            {"key": "unique_signal", "labelKey": "indicatorIde.editor.uniqueBreakouts", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("rsi_divergence_indicator", "RSI Divergence Indicator", "RSI Divergence", "line", {"length": 9, "source": "close", "pivot_left": 1, "pivot_right": 3, "range_lower": 5, "range_upper": 60, "plot_bull": True, "plot_hidden_bull": True, "plot_bear": True, "plot_hidden_bear": False}, [
            {"key": "length", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "open", "high", "low"]},
            {"key": "pivot_left", "labelKey": "indicatorIde.editor.pivotLeft", "type": "number", "min": 1, "max": 20, "step": 1},
            {"key": "pivot_right", "labelKey": "indicatorIde.editor.pivotRight", "type": "number", "min": 1, "max": 20, "step": 1},
            {"key": "range_lower", "labelKey": "indicatorIde.editor.rangeLower", "type": "number", "min": 1, "max": 500, "step": 1},
            {"key": "range_upper", "labelKey": "indicatorIde.editor.rangeUpper", "type": "number", "min": 2, "max": 1000, "step": 1},
            {"key": "plot_bull", "labelKey": "indicatorIde.editor.showBullish", "type": "bool"},
            {"key": "plot_hidden_bull", "labelKey": "indicatorIde.editor.showHiddenBullish", "type": "bool"},
            {"key": "plot_bear", "labelKey": "indicatorIde.editor.showBearish", "type": "bool"},
            {"key": "plot_hidden_bear", "labelKey": "indicatorIde.editor.showHiddenBearish", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("two_b_reversal_pattern", "2B Reversal Pattern (Expo)", "2B Reversal", "band", {"prd": 20, "max_break": 10, "min_break": 3, "setup_src": "close", "confirm_src": "close", "cancel_on_invalid_cross": True, "allow_multiple": False, "signal_mode": "Custom", "bUp": "#6ce5a0", "bDn": "#f23645", "pCol": "#00FFFF"}, [
            {"key": "prd", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "max_break", "labelKey": "indicatorIde.editor.confirmationWindow", "type": "number", "min": 0, "max": 200, "step": 1},
            {"key": "min_break", "labelKey": "indicatorIde.editor.minimumBreakBars", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "setup_src", "labelKey": "indicatorIde.editor.setupSource", "type": "string", "options": ["close", "wick"]},
            {"key": "confirm_src", "labelKey": "indicatorIde.editor.confirmationSource", "type": "string", "options": ["close", "wick"]},
            {"key": "cancel_on_invalid_cross", "labelKey": "indicatorIde.editor.cancelInvalidSetup", "type": "bool"},
            {"key": "allow_multiple", "labelKey": "indicatorIde.editor.allowMultipleSetups", "type": "bool"},
            {"key": "signal_mode", "labelKey": "indicatorIde.editor.signalMode", "type": "string", "options": ["Custom", "Original", "Relaxed", "Aggressive"]},
            {"key": "bUp", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
            {"key": "bDn", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
            {"key": "pCol", "labelKey": "indicatorIde.editor.pivotColor", "type": "color"},
        ], None),
        ChartIndicatorDefinition("alphatrend_screener", "AlphaTrend Screener", "AlphaTrend", "band", {"coeff": 1.0, "period": 14, "use_mfi": True, "show_signal": True}, [
            {"key": "coeff", "labelKey": "indicatorIde.editor.atrCoefficient", "type": "number", "min": 0.1, "max": 10.0, "step": 0.1},
            {"key": "period", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "use_mfi", "labelKey": "indicatorIde.editor.useMfi", "type": "bool"},
            {"key": "show_signal", "labelKey": "indicatorIde.editor.showSignal", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("macd_bollinger_bands", "MACD Bollinger Bands", "MACD BB", "line", {"fast_length": 12, "slow_length": 26, "signal_length": 9, "band_length": 20, "band_multiplier": 2.0, "source": "close", "show_bands": True, "show_signals": True}, [
            {"key": "fast_length", "labelKey": "indicatorIde.editor.fastPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "slow_length", "labelKey": "indicatorIde.editor.slowPeriod", "type": "number", "min": 3, "max": 100, "step": 1},
            {"key": "signal_length", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "band_length", "labelKey": "indicatorIde.editor.bollingerPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "band_multiplier", "labelKey": "indicatorIde.editor.deviation", "type": "number", "min": 0.5, "max": 4.0, "step": 0.1},
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "show_bands", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
            {"key": "show_signals", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("rmi_trend_sniper", "RMI Trend Sniper", "RMI Sniper", "band", {"length": 14, "pmom": 66.0, "nmom": 30.0, "filleshow": True}, [
            {"key": "length", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "pmom", "labelKey": "indicatorIde.editor.positiveMomentumThreshold", "type": "number", "min": 50, "max": 100, "step": 1},
            {"key": "nmom", "labelKey": "indicatorIde.editor.negativeMomentumThreshold", "type": "number", "min": 0, "max": 50, "step": 1},
            {"key": "filleshow", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("smart_money_breakout_signals", "Smart Money Breakout Signals", "SM BOS", "band", {"swing_length": 5, "volume_length": 20, "volume_multiplier": 1.0, "use_volume": True, "show_levels": True}, [
            {"key": "swing_length", "labelKey": "indicatorIde.editor.swingPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "volume_length", "labelKey": "indicatorIde.editor.volumePeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "volume_multiplier", "labelKey": "indicatorIde.editor.volatilityMultiplier", "type": "number", "min": 0.1, "max": 10.0, "step": 0.1},
            {"key": "use_volume", "labelKey": "indicatorIde.editor.useVolumeFilter", "type": "bool"},
            {"key": "show_levels", "labelKey": "indicatorIde.editor.showLevels", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("auto_chart_patterns", "Auto Chart Patterns", "Chart Patterns", "band", {"source": "close", "threshold": 0.01, "min_pivots": 4, "max_pivots": 6, "error_ratio": 0.02, "flat_ratio": 0.2, "conv_eps": 0.05, "allow_channels": True, "allow_wedges": True, "allow_triangles": True, "max_patterns": 6, "avoid_overlap": True}, [
            {"key": "source", "labelKey": "indicatorIde.editor.patternSource", "type": "string", "options": ["close", "hl2"]},
            {"key": "threshold", "labelKey": "indicatorIde.editor.patternThreshold", "type": "number", "min": 0.001, "max": 0.2, "step": 0.001},
            {"key": "min_pivots", "labelKey": "indicatorIde.editor.minimumPivots", "type": "number", "min": 4, "max": 6, "step": 1},
            {"key": "max_pivots", "labelKey": "indicatorIde.editor.maximumPivots", "type": "number", "min": 4, "max": 6, "step": 1},
            {"key": "error_ratio", "labelKey": "indicatorIde.editor.fitErrorTolerance", "type": "number", "min": 0.001, "max": 0.2, "step": 0.001},
            {"key": "flat_ratio", "labelKey": "indicatorIde.editor.flatSlopeRatio", "type": "number", "min": 0.01, "max": 1.0, "step": 0.01},
            {"key": "conv_eps", "labelKey": "indicatorIde.editor.convergenceTolerance", "type": "number", "min": 0.001, "max": 0.5, "step": 0.001},
            {"key": "allow_channels", "labelKey": "indicatorIde.editor.detectChannels", "type": "bool"},
            {"key": "allow_wedges", "labelKey": "indicatorIde.editor.detectWedges", "type": "bool"},
            {"key": "allow_triangles", "labelKey": "indicatorIde.editor.detectTriangles", "type": "bool"},
            {"key": "max_patterns", "labelKey": "indicatorIde.editor.patternHistory", "type": "number", "min": 4, "max": 6, "step": 1},
            {"key": "avoid_overlap", "labelKey": "indicatorIde.editor.avoidPatternOverlap", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("divergence_many_indicators", "Divergence for Many Indicators v4", "Multi Divergence", "line", {"pivot_period": 5, "source": "Close", "div_type": "Regular", "max_bars": 100, "show_names": "Full", "show_number": True, "calc_macd": True, "calc_hist": True, "calc_rsi": True, "calc_stoch": True, "calc_cci": True, "calc_mom": True, "calc_obv": True, "calc_vwmacd": True, "calc_cmf": True, "calc_mfi": True, "calc_ext": False}, [
            {"key": "pivot_period", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 20, "step": 1},
            {"key": "source", "labelKey": "indicatorIde.editor.divergenceSource", "type": "string", "options": ["Close", "High/Low"]},
            {"key": "div_type", "labelKey": "indicatorIde.editor.divergenceType", "type": "string", "options": ["Regular", "Hidden", "Both"]},
            {"key": "max_bars", "labelKey": "indicatorIde.editor.maximumPivotDistance", "type": "number", "min": 10, "max": 500, "step": 10},
            {"key": "show_names", "labelKey": "indicatorIde.editor.signalDetail", "type": "string", "options": ["Full", "Short", "None"]},
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
        ], None),
        ChartIndicatorDefinition("trading_abc", "Trading ABC", "Trading ABC", "band", {"prd": 8, "fiboup": 0.618, "fibodn": 0.382, "errorrate": 5.0, "src_ma": "close", "malen1": 50, "malen2": 100, "malen3": 150, "malen4": 200, "malen5": 20, "malen6": 40, "showabc": True, "keepabc": True, "showcloud": True, "showzigzag": True}, [
            {"key": "prd", "labelKey": "indicatorIde.editor.pivotPeriod", "type": "number", "min": 2, "max": 40, "step": 1},
            {"key": "fiboup", "labelKey": "indicatorIde.editor.upperRetracement", "type": "number", "min": 0.1, "max": 1.5, "step": 0.001},
            {"key": "fibodn", "labelKey": "indicatorIde.editor.lowerRetracement", "type": "number", "min": 0.1, "max": 1.5, "step": 0.001},
            {"key": "errorrate", "labelKey": "indicatorIde.editor.ratioTolerance", "type": "number", "min": 0, "max": 25, "step": 0.5},
            {"key": "src_ma", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "malen1", "labelKey": "indicatorIde.editor.smaLength1", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "malen2", "labelKey": "indicatorIde.editor.smaLength2", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "malen3", "labelKey": "indicatorIde.editor.smaLength3", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "malen4", "labelKey": "indicatorIde.editor.smaLength4", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "malen5", "labelKey": "indicatorIde.editor.emaLength1", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "malen6", "labelKey": "indicatorIde.editor.emaLength2", "type": "number", "min": 2, "max": 300, "step": 1},
            {"key": "showabc", "labelKey": "indicatorIde.editor.showAbcLine", "type": "bool"},
            {"key": "keepabc", "labelKey": "indicatorIde.editor.keepConfirmedAbc", "type": "bool"},
            {"key": "showcloud", "labelKey": "indicatorIde.editor.useTrendFilter", "type": "bool"},
            {"key": "showzigzag", "labelKey": "indicatorIde.editor.showZigzag", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("pmax_on_rsi_t3", "PMax on RSI w T3", "PMax RSI T3", "line", {"source": "hl2", "multiplier": 1.0, "t3_length": 8, "t3_factor": 0.7, "atr_length": 10, "rsi_length": 14, "show_rsi": True, "show_support": True, "show_signals": True, "highlighting": True}, [
            {"key": "source", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["hl2", "hlc3", "close", "open", "high", "low"]},
            {"key": "multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1},
            {"key": "t3_length", "labelKey": "indicatorIde.editor.t3Period", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "t3_factor", "labelKey": "indicatorIde.editor.smoothingFactor", "type": "number", "min": 0, "max": 1, "step": 0.05},
            {"key": "atr_length", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "rsi_length", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "show_rsi", "labelKey": "indicatorIde.editor.showRsi", "type": "bool"},
            {"key": "show_support", "labelKey": "indicatorIde.editor.showSupport", "type": "bool"},
            {"key": "show_signals", "labelKey": "indicatorIde.editor.showSignals", "type": "bool"},
            {"key": "highlighting", "labelKey": "indicatorIde.editor.highlightTrend", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("volume_weighted_macd", "Volume Weighted MACD", "VW-MACD", "line", {"fast_length": 12, "slow_length": 26, "signal_length": 9, "histogram": True}, [
            {"key": "fast_length", "labelKey": "indicatorIde.editor.fastPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "slow_length", "labelKey": "indicatorIde.editor.slowPeriod", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_length", "labelKey": "indicatorIde.editor.signalPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "histogram", "labelKey": "indicatorIde.editor.showHistogram", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("itg_scalper", "ITG Scalper", "ITG Scalper", "band", {"fast_length": 5, "slow_length": 13, "atr_length": 14, "atr_multiplier": 1.5, "show_bands": True}, [
            {"key": "fast_length", "labelKey": "indicatorIde.editor.fastPeriod", "type": "number", "min": 2, "max": 50, "step": 1},
            {"key": "slow_length", "labelKey": "indicatorIde.editor.slowPeriod", "type": "number", "min": 3, "max": 100, "step": 1},
            {"key": "atr_length", "labelKey": "indicatorIde.editor.atrPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "atr_multiplier", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 5.0, "step": 0.1},
            {"key": "show_bands", "labelKey": "indicatorIde.editor.showBands", "type": "bool"},
        ], None),
        ChartIndicatorDefinition("machine_learning_rsi", "Machine Learning RSI", "ML RSI", "line", {"rsi_length": 14, "use_smoothing": True, "smoothing_length": 3, "ma_type": "ALMA", "alma_sigma": 4.0, "use_knn": True, "knn_neighbors": 5, "knn_lookback": 100, "knn_weight": 0.4, "feature_count": 3, "use_filter": True, "filter_method": "Kalman", "filter_strength": 0.3, "src": "close", "overbought": 70, "oversold": 30, "color_scheme": "Classic", "neon_effect": True, "color_mode": "Trend Following", "show_table": True, "table_position": "top-left"}, [
            {"key": "rsi_length", "labelKey": "indicatorIde.editor.rsiPeriod", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "use_smoothing", "labelKey": "indicatorIde.editor.useSmoothing", "type": "bool"},
            {"key": "smoothing_length", "labelKey": "indicatorIde.editor.smoothing", "type": "number", "min": 1, "max": 50, "step": 1},
            {"key": "ma_type", "labelKey": "indicatorIde.editor.smoothingMethod", "type": "string", "options": ["SMA", "EMA", "DEMA", "TEMA", "WMA", "VWMA", "SMMA", "HMA", "LSMA", "ALMA"]},
            {"key": "alma_sigma", "labelKey": "indicatorIde.editor.almaSigma", "type": "number", "min": 1, "max": 10, "step": 0.5},
            {"key": "use_knn", "labelKey": "indicatorIde.editor.enableKnn", "type": "bool"},
            {"key": "knn_neighbors", "labelKey": "indicatorIde.editor.knnNeighbors", "type": "number", "min": 1, "max": 32, "step": 1},
            {"key": "knn_lookback", "labelKey": "indicatorIde.editor.knnLookback", "type": "number", "min": 20, "max": 500, "step": 10},
            {"key": "knn_weight", "labelKey": "indicatorIde.editor.knnWeight", "type": "number", "min": 0, "max": 1, "step": 0.05},
            {"key": "feature_count", "labelKey": "indicatorIde.editor.featureCount", "type": "number", "min": 1, "max": 5, "step": 1},
            {"key": "use_filter", "labelKey": "indicatorIde.editor.applyRsiFilter", "type": "bool"},
            {"key": "filter_method", "labelKey": "indicatorIde.editor.filterMethod", "type": "string", "options": ["Kalman", "DoubleEMA", "ALMA"]},
            {"key": "filter_strength", "labelKey": "indicatorIde.editor.filterStrength", "type": "number", "min": 0.05, "max": 1, "step": 0.05},
            {"key": "src", "labelKey": "indicatorIde.editor.priceSource", "type": "string", "options": ["close", "hl2", "hlc3", "ohlc4"]},
            {"key": "overbought", "labelKey": "indicatorIde.editor.overbought", "type": "number", "min": 50, "max": 95, "step": 1},
            {"key": "oversold", "labelKey": "indicatorIde.editor.oversold", "type": "number", "min": 5, "max": 50, "step": 1},
            {"key": "color_scheme", "labelKey": "indicatorIde.editor.colorScheme", "type": "string", "options": ["Classic", "Deuteranopia", "Protanopia", "Tritanopia", "Monochrome"]},
            {"key": "neon_effect", "labelKey": "indicatorIde.editor.neonEffect", "type": "bool"},
            {"key": "color_mode", "labelKey": "indicatorIde.editor.colorMode", "type": "string", "options": ["None", "Trend Following", "Impulse"]},
            {"key": "show_table", "labelKey": "indicatorIde.editor.compatibilityTable", "type": "bool"},
            {"key": "table_position", "labelKey": "indicatorIde.editor.compatibilityTablePosition", "type": "string"},
        ], None),
        ChartIndicatorDefinition("ghost_tangent_crossings", "Ghost Tangent Crossings", "Ghost Tangents", "band", {"pivot_type": "Wick", "pivot_forward": 25, "show_elliptical_zig": True, "show_ghosts": True, "show_break": True, "max_zig": 0, "equipoint_style": "Directional", "extend_line": False, "up_color": "#1bcf66", "down_color": "#ee2d2d", "ghost_up_color": "#1bcf663a", "ghost_down_color": "#ee2d2d3a", "text_color": "#EEEEEE"}, [
            {"key": "pivot_type", "labelKey": "indicatorIde.editor.pivotSource", "type": "string", "options": ["Wick", "Body"]},
            {"key": "pivot_forward", "labelKey": "indicatorIde.editor.pivotRight", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "show_elliptical_zig", "labelKey": "indicatorIde.editor.showConfirmedSwings", "type": "bool"},
            {"key": "show_ghosts", "labelKey": "indicatorIde.editor.showProvisionalSwings", "type": "bool"},
            {"key": "show_break", "labelKey": "indicatorIde.editor.showTangentCrossings", "type": "bool"},
            {"key": "max_zig", "labelKey": "indicatorIde.editor.maximumSwings", "type": "number", "min": 0, "max": 100, "step": 1},
            {"key": "equipoint_style", "labelKey": "indicatorIde.editor.equipointStyle", "type": "string", "options": ["Directional", "Horizontal", "None"]},
            {"key": "extend_line", "labelKey": "indicatorIde.editor.extendProjection", "type": "bool"},
            {"key": "up_color", "labelKey": "indicatorIde.editor.bullishColor", "type": "string"},
            {"key": "down_color", "labelKey": "indicatorIde.editor.bearishColor", "type": "string"},
            {"key": "ghost_up_color", "labelKey": "indicatorIde.editor.ghostBullishColor", "type": "string"},
            {"key": "ghost_down_color", "labelKey": "indicatorIde.editor.ghostBearishColor", "type": "string"},
            {"key": "text_color", "labelKey": "indicatorIde.editor.markerTextColor", "type": "string"},
        ], None),
        ChartIndicatorDefinition("volume_supertrend_ai", "Volume SuperTrend AI", "Volume ST AI", "band", {"k": 3, "n_data": 10, "knn_price_len": 20, "knn_st_len": 100, "ai_signals": True, "bullish_col": "#00FF00", "bearish_col": "#FF0000", "length": 10, "factor": 3.0, "ma_src": "WMA", "up_col": "#00FF00", "dn_col": "#FF0000", "ne_col": "#0000FF", "show_cloud": True, "cloud_bull": "#00FF00", "cloud_bear": "#FF0000", "cloud_transp": 78, "cloud_ref_len": 10, "cloud_line_smooth": 2, "cloud_layers": 3}, [
            {"key": "k", "labelKey": "indicatorIde.editor.knnNeighbors", "type": "number", "min": 1, "max": 32, "step": 1},
            {"key": "n_data", "labelKey": "indicatorIde.editor.knnHistoryWindow", "type": "number", "min": 1, "max": 500, "step": 1},
            {"key": "knn_price_len", "labelKey": "indicatorIde.editor.priceWmaPeriod", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "knn_st_len", "labelKey": "indicatorIde.editor.supertrendWmaPeriod", "type": "number", "min": 2, "max": 500, "step": 1},
            {"key": "ai_signals", "labelKey": "indicatorIde.editor.showAiSignals", "type": "bool"},
            {"key": "bullish_col", "labelKey": "indicatorIde.editor.bullishSignalColor", "type": "color"},
            {"key": "bearish_col", "labelKey": "indicatorIde.editor.bearishSignalColor", "type": "color"},
            {"key": "length", "labelKey": "indicatorIde.editor.period", "type": "number", "min": 2, "max": 200, "step": 1},
            {"key": "factor", "labelKey": "indicatorIde.editor.multiplier", "type": "number", "min": 0.1, "max": 10, "step": 0.1},
            {"key": "ma_src", "labelKey": "indicatorIde.editor.movingAverageType", "type": "string", "options": ["SMA", "EMA", "WMA", "RMA", "VWMA"]},
            {"key": "up_col", "labelKey": "indicatorIde.editor.bullishColor", "type": "color"},
            {"key": "dn_col", "labelKey": "indicatorIde.editor.bearishColor", "type": "color"},
            {"key": "ne_col", "labelKey": "indicatorIde.editor.neutralColor", "type": "color"},
            {"key": "show_cloud", "labelKey": "indicatorIde.editor.showCloud", "type": "bool"},
            {"key": "cloud_bull", "labelKey": "indicatorIde.editor.bullishCloudColor", "type": "color"},
            {"key": "cloud_bear", "labelKey": "indicatorIde.editor.bearishCloudColor", "type": "color"},
            {"key": "cloud_transp", "labelKey": "indicatorIde.editor.cloudTransparency", "type": "number", "min": 0, "max": 100, "step": 1},
            {"key": "cloud_ref_len", "labelKey": "indicatorIde.editor.cloudReferencePeriod", "type": "number", "min": 1, "max": 200, "step": 1},
            {"key": "cloud_line_smooth", "labelKey": "indicatorIde.editor.cloudSmoothing", "type": "number", "min": 1, "max": 100, "step": 1},
            {"key": "cloud_layers", "labelKey": "indicatorIde.editor.cloudLayers", "type": "number", "min": 1, "max": 3, "step": 1},
        ], None),
        ChartIndicatorDefinition("chip_distribution", "Chip Distribution", "Chip", "profile", {"lookback": 120, "rows": 48, "value_area_percent": 70}, [
            {"key": "lookback", "labelKey": "indicatorIde.editor.lookback", "type": "number", "min": 10, "max": 5000, "step": 1},
            {"key": "rows", "labelKey": "indicatorIde.chipDistribution.priceLevels", "type": "number", "min": 8, "max": 120, "step": 1},
            {"key": "value_area_percent", "labelKey": "indicatorIde.chipDistribution.valueAreaPercent", "type": "number", "min": 50, "max": 99, "step": 1},
        ], _chip_distribution, True),
        ChartIndicatorDefinition("z_score", "Z-Score", "Z-Score", "line", {"period": 20}, _period_schema("period", maximum=300), None),
        ChartIndicatorDefinition("pvo", "Percentage Volume Oscillator", "PVO", "line", {"short_period": 12, "long_period": 26, "signal_period": 9}, [
            {"key": "short_period", "labelKey": "indicatorIde.editor.fastLine", "type": "number", "min": 2, "max": 100, "step": 1},
            {"key": "long_period", "labelKey": "indicatorIde.editor.slowLine", "type": "number", "min": 3, "max": 200, "step": 1},
            {"key": "signal_period", "labelKey": "indicatorIde.editor.signalLine", "type": "number", "min": 1, "max": 100, "step": 1},
        ], None),
        ChartIndicatorDefinition("nvi", "Negative Volume Index", "NVI", "line", {}, [], None),
    ]
    return {item.indicator_id: item for item in defs}


_DEFINITIONS = _make_definitions()


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
            results.append({"id": indicator_id, "requestKey": request_key, "success": False, "error": "indicator.notFound"})
            continue
        raw_params = item.get("params") if isinstance(item.get("params"), Mapping) else {}
        params = {**definition.default_params, **raw_params}
        try:
            if indicator_id in _SOURCE_FILES:
                params = _normalize_source_params(definition, params)
                result = _compute_indicator_source(indicator_id, definition, frame, params)
            else:
                if definition.compute is None:
                    raise RuntimeError("indicator implementation is missing")
                result = definition.compute(frame, params)
            result.update({"id": indicator_id, "requestKey": request_key, "success": True, "params": params})
            results.append(result)
        except ValueError as exc:
            results.append({"id": indicator_id, "requestKey": request_key, "success": False, "error": str(exc)})
        except Exception:
            results.append({"id": indicator_id, "requestKey": request_key, "success": False, "error": "indicator.computeFailed"})
    return results
