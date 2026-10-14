# ============================================================
# [Default] False Breakout (Expo)
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal false-breakout detector adapted from MiniBT's
# False Breakout (Expo) indicator. It produces chart lines and visual
# markers only; it never creates, submits, or manages trading orders.
# ============================================================

my_indicator_name = "[Default] False Breakout (Expo)"
my_indicator_description = (
    "Consecutive new-high/new-low false-breakout detector with causal levels "
    "and chart-only reversal signals."
)

# @param prd int 20 New-high/new-low lookback range=2:200:1
# @param minperiod int 5 Minimum separation between the two breakout events range=1:200:1
# @param maxperiod int 5 Signal validity window after the latest breakout range=0:200:1
# @param ma_type string None Channel smoothing: None, WMA, or HMA
# @param length int 10 Smoothing period for WMA/HMA range=2:200:1
# @param aggressive bool False Use low/high for the high/low channel sources


def as_bool(value, default=False):
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


def finite(value):
    return bool(np.isfinite(value))


def wma(values, period):
    """Trailing weighted average; missing values stay unavailable."""
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    weights = np.arange(1, period + 1, dtype=float)
    denominator = float(np.sum(weights))
    for index in range(period - 1, len(values)):
        window = values[index - period + 1:index + 1]
        if np.all(np.isfinite(window)):
            result[index] = float(np.dot(window, weights) / denominator)
    return result


def hma(values, period):
    period = max(2, int(period))
    half = max(1, period // 2)
    root = max(1, int(np.sqrt(period)))
    raw = 2.0 * wma(values, half) - wma(values, period)
    return wma(raw, root)


def smooth(values, ma_type, period):
    normalized = str(ma_type).strip().lower()
    if normalized in ("none", "", "💎"):
        return np.asarray(values, dtype=float).copy()
    if normalized == "wma":
        return wma(values, period)
    if normalized == "hma":
        return hma(values, period)
    return np.asarray(values, dtype=float).copy()


def rolling_extreme(values, period, find_max):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    for index in range(period - 1, len(values)):
        window = values[index - period + 1:index + 1]
        if np.all(np.isfinite(window)):
            result[index] = float(np.max(window) if find_max else np.min(window))
    return result


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


prd = clamp_int(params.get("prd", 20), 20, 2, 200)
minperiod = clamp_int(params.get("minperiod", 5), 5, 1, 200)
maxperiod = clamp_int(params.get("maxperiod", 5), 5, 0, 200)
length = clamp_int(params.get("length", 10), 10, 2, 200)
ma_type = str(params.get("ma_type", "None")).strip()
if ma_type not in ("None", "WMA", "HMA", "none", "wma", "hma", "💎"):
    ma_type = "None"
aggressive = as_bool(params.get("aggressive", False), False)


df = df.copy()
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
n = len(close)

# Normal mode detects new extremes in wick prices. Aggressive mode uses the
# opposite wick for the channel, matching MiniBT's documented behavior.
hi_source = low if aggressive else high
lo_source = high if aggressive else low
hi_raw = rolling_extreme(hi_source, prd, True)
lo_raw = rolling_extreme(lo_source, prd, False)
hi = smooth(hi_raw, ma_type, length)
lo = smooth(lo_raw, ma_type, length)

val = np.full(n, np.nan, dtype=float)
count = np.zeros(n, dtype=int)
false_break_up = np.full(n, np.nan, dtype=float)
false_break_down = np.full(n, np.nan, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)

# These are the latest two confirmed channel-break bars. Keeping the indices
# as state avoids looking ahead and reproduces the minperiod/maxperiod window.
latest_breakout = None
previous_breakout = None
current_count = 0
current_val = np.nan
active_up_level = np.nan
active_down_level = np.nan

for i in range(n):
    previous_val = current_val
    previous_close = close[i - 1] if i > 0 else np.nan
    previous_count = current_count

    cond_hi = (
        i >= 2
        and finite(hi[i])
        and finite(hi[i - 1])
        and finite(hi[i - 2])
        and hi[i] > hi[i - 1]
        and hi[i - 1] <= hi[i - 2]
    )
    cond_lo = (
        i >= 2
        and finite(lo[i])
        and finite(lo[i - 1])
        and finite(lo[i - 2])
        and lo[i] < lo[i - 1]
        and lo[i - 1] >= lo[i - 2]
    )

    # A bar cannot normally be both a new high and a new low, but process both
    # deterministically if malformed input makes that possible.
    if cond_hi:
        previous_breakout = latest_breakout
        latest_breakout = i
        current_count -= 1
        current_val = low[i] if finite(low[i]) else current_val
    if cond_lo:
        previous_breakout = latest_breakout
        latest_breakout = i
        current_count += 1
        current_val = high[i] if finite(high[i]) else current_val

    # Pine's crossunder/crossover compare the current and previous values of
    # both series. This is causal even though the trigger level can change.
    cross_down = (
        finite(close[i])
        and finite(current_val)
        and finite(previous_close)
        and finite(previous_val)
        and close[i] < current_val
        and previous_close >= previous_val
    )
    cross_up = (
        finite(close[i])
        and finite(current_val)
        and finite(previous_close)
        and finite(previous_val)
        and close[i] > current_val
        and previous_close <= previous_val
    )

    window_ready = (
        latest_breakout is not None
        and previous_breakout is not None
        and previous_breakout + minperiod < latest_breakout
        and i - maxperiod <= latest_breakout
    )
    if window_ready and current_count < -1 and cross_down:
        short_signal[i] = True
        active_up_level = current_val
        current_count = 0
    elif window_ready and current_count > 1 and cross_up:
        long_signal[i] = True
        active_down_level = current_val
        current_count = 0

    # Horizontal lines start when the signal is confirmed and remain visible
    # until the next signal of the same type. This avoids repainting historical
    # bars when a later bar confirms a false breakout.
    if finite(active_up_level):
        false_break_up[i] = active_up_level
    if finite(active_down_level):
        false_break_down[i] = active_down_level

    val[i] = current_val
    count[i] = current_count

long_marks = [
    float(low[i]) if long_signal[i] and finite(low[i]) else None
    for i in range(n)
]
short_marks = [
    float(high[i]) if short_signal[i] and finite(high[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "False Break Up",
            "data": plot_list(false_break_up),
            "color": "#f23645",
            "width": 2,
            "overlay": True,
        },
        {
            "name": "False Break Down",
            "data": plot_list(false_break_down),
            "color": "#6ce5a0",
            "width": 2,
            "overlay": True,
        },
    ],
    "signals": [
        {
            "type": "buy",
            "text": "False Break Down",
            "data": long_marks,
            "color": "#6ce5a0",
            "anchor": "low",
            "shape": "triangle",
        },
        {
            "type": "sell",
            "text": "False Break Up",
            "data": short_marks,
            "color": "#f23645",
            "anchor": "high",
            "shape": "inverted_triangle",
        },
    ],
    "metadata": {
        "causal": True,
        "prd": prd,
        "minperiod": minperiod,
        "maxperiod": maxperiod,
        "ma_type": ma_type.lower(),
        "length": length,
        "aggressive": aggressive,
        "hi": plot_list(hi),
        "lo": plot_list(lo),
        "val": plot_list(val),
        "count": [int(value) for value in count],
    },
    "layers": [],
}
