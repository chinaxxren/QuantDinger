# ============================================================
# [Default] ITG Scalper
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal EMA/ATR scalper overlay. Signals are chart markers only.
# ============================================================

my_indicator_name = "[Default] ITG Scalper"
my_indicator_description = "Fast and slow trend filters with ATR scalp bands and causal crossover markers."

# @param fast_length int 5 Fast EMA length range=2:50:1
# @param slow_length int 13 Slow EMA length range=3:100:1
# @param atr_length int 14 ATR lookback range=2:100:1
# @param atr_multiplier float 1.5 ATR band multiplier range=0.1:5.0:0.1
# @param show_bands bool True Show ATR scalp bands


def _clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if not np.isfinite(parsed):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _as_bool(value, default):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "off", "")


def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


fast_length = _clamp_int(params.get("fast_length", 5), 5, 2, 50)
slow_length = _clamp_int(params.get("slow_length", 13), 13, 3, 100)
if slow_length <= fast_length:
    slow_length = min(100, fast_length + 1)
atr_length = _clamp_int(params.get("atr_length", 14), 14, 2, 100)
atr_multiplier = _clamp_float(params.get("atr_multiplier", 1.5), 1.5, 0.1, 5.0)
show_bands = _as_bool(params.get("show_bands", True), True)

frame = df.copy()
open_values = frame["open"].astype(float).to_numpy(dtype=float)
high = frame["high"].astype(float)
low = frame["low"].astype(float)
close = frame["close"].astype(float)
close_values = close.to_numpy(dtype=float)
n = len(frame)

fast = close.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean().to_numpy(dtype=float)
slow = close.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean().to_numpy(dtype=float)
true_range = pd.concat(
    [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1
).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean().to_numpy(dtype=float)

basis = slow
upper = basis + atr_multiplier * atr
lower = basis - atr_multiplier * atr
previous_fast = np.concatenate(([np.nan], fast[:-1]))
previous_slow = np.concatenate(([np.nan], slow[:-1]))
finite_cross = np.isfinite(fast) & np.isfinite(slow) & np.isfinite(previous_fast) & np.isfinite(previous_slow)
buy = finite_cross & (previous_fast <= previous_slow) & (fast > slow)
sell = finite_cross & (previous_fast >= previous_slow) & (fast < slow)

if not show_bands:
    upper = np.full(n, np.nan, dtype=float)
    lower = np.full(n, np.nan, dtype=float)

buy_marks = [float(low.iloc[i]) * 0.995 if buy[i] and np.isfinite(low.iloc[i]) else None for i in range(n)]
sell_marks = [float(high.iloc[i]) * 1.005 if sell[i] and np.isfinite(high.iloc[i]) else None for i in range(n)]
trend = np.where(np.isfinite(fast) & np.isfinite(slow) & (fast >= slow), 1, -1)
trend = [int(value) if np.isfinite(value) else 0 for value in trend]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Fast EMA", "data": _plot_list(fast), "color": "#26A69A", "overlay": True, "width": 1},
        {"name": "Slow EMA", "data": _plot_list(slow), "color": "#FFB300", "overlay": True, "width": 2},
        {"name": "Scalp Upper", "data": _plot_list(upper), "color": "#90CAF9", "overlay": True},
        {"name": "Scalp Lower", "data": _plot_list(lower), "color": "#90CAF9", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "ITG Buy", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "ITG Sell", "data": sell_marks, "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "fast_length": fast_length,
        "slow_length": slow_length,
        "atr_length": atr_length,
        "atr_multiplier": atr_multiplier,
        "show_bands": show_bands,
        "trend": trend,
    },
}
