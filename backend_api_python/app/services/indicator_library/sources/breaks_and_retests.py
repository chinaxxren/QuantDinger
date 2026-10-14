# ============================================================
# [Default] Breaks and Retests
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal support/resistance boxes inspired by Breaks and Retests [HG].
# Pivot levels become available only after right-side confirmation.  Breakout
# and retest markers are visual events only and never place trades.
# ============================================================

my_indicator_name = "[Default] Breaks and Retests"
my_indicator_description = (
    "Causal pivot support/resistance levels with breakout and retest markers."
)

# @param lookback int 20 Pivot left/right confirmation range=2:100:1
# @param ret_since int 2 Bars after a break in which a retest may begin range=0:50:1
# @param ret_valid int 2 Retest confirmation window range=0:50:1
# @param breakouts bool True Show breakout signals
# @param retests bool True Show retest signals
# @param support_color string #FF0000 Support color
# @param resistance_color string #089981 Resistance color


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


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


lookback = clamp_int(params.get("lookback", 20), 20, 2, 100)
ret_since = clamp_int(params.get("ret_since", 2), 2, 0, 50)
ret_valid = clamp_int(params.get("ret_valid", 2), 2, 0, 50)
show_breakouts = as_bool(params.get("breakouts", True), True)
show_retests = as_bool(params.get("retests", True), True)
support_color = str(params.get("support_color", "#FF0000"))
resistance_color = str(params.get("resistance_color", "#089981"))

df = df.copy()
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
n = len(close)

support = np.full(n, np.nan, dtype=float)
resistance = np.full(n, np.nan, dtype=float)
support_top = np.full(n, np.nan, dtype=float)
resistance_bottom = np.full(n, np.nan, dtype=float)
long_signal = np.full(n, np.nan, dtype=float)
short_signal = np.full(n, np.nan, dtype=float)

# A pivot at `pivot_index` is only accepted on the current confirmation bar.
# Levels are then projected forward, so no historical output is backfilled.
active_support = np.nan
active_resistance = np.nan
support_broken = False
resistance_broken = False
support_break_index = None
resistance_break_index = None
support_retest_emitted = False
resistance_retest_emitted = False

for i in range(n):
    pivot_index = i - lookback
    if pivot_index >= lookback:
        left_high = high[pivot_index - lookback:pivot_index]
        right_high = high[pivot_index + 1:i + 1]
        left_low = low[pivot_index - lookback:pivot_index]
        right_low = low[pivot_index + 1:i + 1]
        if (
            np.isfinite(high[pivot_index])
            and np.all(np.isfinite(left_high))
            and np.all(np.isfinite(right_high))
            and high[pivot_index] >= np.max(right_high)
            and high[pivot_index] > np.max(left_high)
        ):
            active_resistance = float(high[pivot_index])
            resistance_broken = False
            resistance_break_index = None
            resistance_retest_emitted = False
        if (
            np.isfinite(low[pivot_index])
            and np.all(np.isfinite(left_low))
            and np.all(np.isfinite(right_low))
            and low[pivot_index] <= np.min(right_low)
            and low[pivot_index] < np.min(left_low)
        ):
            active_support = float(low[pivot_index])
            support_broken = False
            support_break_index = None
            support_retest_emitted = False

    if np.isfinite(active_support):
        support[i] = active_support
        # A compact box-like lower boundary.  The renderer still receives a
        # normal overlay series and therefore keeps the existing chart layout.
        support_top[i] = active_support
    if np.isfinite(active_resistance):
        resistance[i] = active_resistance
        resistance_bottom[i] = active_resistance

    previous_close = close[i - 1] if i else np.nan
    if np.isfinite(active_resistance) and not resistance_broken:
        if np.isfinite(previous_close) and previous_close <= active_resistance < close[i]:
            resistance_broken = True
            resistance_break_index = i
            if show_breakouts:
                long_signal[i] = low[i]
    if np.isfinite(active_support) and not support_broken:
        if np.isfinite(previous_close) and previous_close >= active_support > close[i]:
            support_broken = True
            support_break_index = i
            if show_breakouts:
                short_signal[i] = high[i]

    # Retest means price returns to the broken level after a configurable
    # waiting period and confirms back on the breakout side.
    if resistance_broken and resistance_break_index is not None:
        age = i - resistance_break_index
        if age > ret_since and age <= ret_since + ret_valid + 1 and not resistance_retest_emitted:
            touched = low[i] <= active_resistance <= high[i]
            confirmed = close[i] > active_resistance
            if touched and confirmed:
                if show_retests:
                    long_signal[i] = low[i]
                resistance_retest_emitted = True
    if support_broken and support_break_index is not None:
        age = i - support_break_index
        if age > ret_since and age <= ret_since + ret_valid + 1 and not support_retest_emitted:
            touched = low[i] <= active_support <= high[i]
            confirmed = close[i] < active_support
            if touched and confirmed:
                if show_retests:
                    short_signal[i] = high[i]
                support_retest_emitted = True

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Support", "data": plot_list(support), "color": support_color, "overlay": True},
        {"name": "Resistance", "data": plot_list(resistance), "color": resistance_color, "overlay": True},
        {"name": "Support Box Boundary", "data": plot_list(support_top), "color": support_color, "overlay": True},
        {"name": "Resistance Box Boundary", "data": plot_list(resistance_bottom), "color": resistance_color, "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Break/Retest", "data": plot_list(long_signal), "color": resistance_color},
        {"type": "sell", "text": "Break/Retest", "data": plot_list(short_signal), "color": support_color},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "lookback": lookback,
        "ret_since": ret_since,
        "ret_valid": ret_valid,
    },
}
