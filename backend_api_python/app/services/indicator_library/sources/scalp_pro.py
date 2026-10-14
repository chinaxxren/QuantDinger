# ============================================================
# [Default] Scalp Pro
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Ehlers two-pole SuperSmoother MACD-style oscillator.  All values are
# calculated from the current and completed historical bars only; signals are
# chart markers and never submit or manage orders.
# ============================================================

my_indicator_name = "[Default] Scalp Pro"
my_indicator_description = (
    "Scalp Pro SuperSmoother MACD oscillator with causal crossover markers."
)

# @param fast_length int 8 Fast SuperSmoother period range=1:200:1
# @param slow_length int 10 Slow SuperSmoother period range=2:500:1
# @param smooth_length int 8 Signal smoothing period range=1:200:1
# @param scale float 10000000.0 MACD display scale range=0.0001:100000000.0:0.0001
# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param show_fill bool True Fill area between MACD and signal
# @param show_signals bool True Show buy/sell chart markers
# @param qty int 1 Compatibility quantity; visual only


def as_bool(value, default):
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("false", "0", "no", "off"):
        return False
    if text in ("true", "1", "yes", "on"):
        return True
    return bool(value)


def clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if not np.isfinite(parsed):
        parsed = default
    return min(maximum, max(minimum, parsed))


def selected_source(frame, name):
    normalized = str(name or "close").strip().lower()
    open_price = frame["open"].astype(float).to_numpy(copy=True)
    high = frame["high"].astype(float).to_numpy(copy=True)
    low = frame["low"].astype(float).to_numpy(copy=True)
    close = frame["close"].astype(float).to_numpy(copy=True)
    columns = {
        "close": close,
        "hl2": (high + low) / 2.0,
        "hlc3": (high + low + close) / 3.0,
        "ohlc4": (open_price + high + low + close) / 4.0,
    }
    if normalized not in columns:
        normalized = "close"
    return columns[normalized], normalized


def super_smoother(values, length):
    """Apply the causal Ehlers two-pole SuperSmoother filter."""
    result = np.full(len(values), np.nan, dtype=float)
    angle = 1.414 * np.pi / float(length)
    decay = np.exp(-angle)
    c2 = 2.0 * decay * np.cos(angle)
    c3 = -(decay * decay)
    c1 = 1.0 - c2 - c3
    previous_price = 0.0
    previous_one = 0.0
    previous_two = 0.0
    for i, value in enumerate(values):
        if not np.isfinite(value):
            continue
        filtered = (
            c1 * (float(value) + previous_price) / 2.0
            + c2 * previous_one
            + c3 * previous_two
        )
        result[i] = filtered
        previous_price = float(value)
        previous_two = previous_one
        previous_one = filtered
    return result


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


fast_length = clamp_int(params.get("fast_length", 8), 8, 1, 200)
slow_length = clamp_int(params.get("slow_length", 10), 10, 2, 500)
if slow_length <= fast_length:
    slow_length = min(500, fast_length + 1)
smooth_length = clamp_int(params.get("smooth_length", 8), 8, 1, 200)
scale = clamp_float(params.get("scale", 10000000.0), 10000000.0, 0.0001, 100000000.0)
source, source_name = selected_source(df, params.get("source", "close"))
show_fill = as_bool(params.get("show_fill", True), True)
show_signals = as_bool(params.get("show_signals", True), True)
qty = clamp_int(params.get("qty", 1), 1, 1, 1000000)

fast_smoothed = super_smoother(source, fast_length)
slow_smoothed = super_smoother(source, slow_length)
macd = (fast_smoothed - slow_smoothed) * scale
signal = super_smoother(macd, smooth_length)

previous_macd = np.concatenate(([np.nan], macd[:-1]))
previous_signal = np.concatenate(([np.nan], signal[:-1]))
finite_cross = (
    np.isfinite(macd)
    & np.isfinite(signal)
    & np.isfinite(previous_macd)
    & np.isfinite(previous_signal)
)
buy = finite_cross & (previous_macd <= previous_signal) & (macd > signal)
sell = finite_cross & (previous_macd >= previous_signal) & (macd < signal)

if show_signals:
    buy_marks = [float(macd[i]) if buy[i] else None for i in range(len(macd))]
    sell_marks = [float(macd[i]) if sell[i] else None for i in range(len(macd))]
else:
    buy_marks = [None] * len(macd)
    sell_marks = [None] * len(macd)

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "MACD",
            "data": plot_list(macd),
            "color": "#217A21",
            "overlay": False,
            "width": 2,
        },
        {
            "name": "Signal",
            "data": plot_list(signal),
            "color": "#FFFF00",
            "overlay": False,
            "width": 1,
        },
    ],
    "signals": [
        {"type": "buy", "text": "Buy", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "Sell", "data": sell_marks, "color": "#FF0000"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "fast_length": fast_length,
        "slow_length": slow_length,
        "smooth_length": smooth_length,
        "scale": scale,
        "source": source_name,
        "show_fill": show_fill,
        "show_signals": show_signals,
        "qty": qty,
        "ssmooth": plot_list(fast_smoothed),
        "ssmooth2": plot_list(slow_smoothed),
        "macd": plot_list(macd),
        "signal": plot_list(signal),
        "long_signal": [bool(value) for value in buy],
        "short_signal": [bool(value) for value in sell],
    },
}
