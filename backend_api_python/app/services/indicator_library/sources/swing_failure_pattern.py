# ============================================================
# [Default] Swing Failure Pattern
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal SFP detector inspired by Swing Failure Pattern [LuxAlgo]. A swing is
# confirmed only after right-side bars are available; no historical values are
# backfilled when the pivot becomes known. Signals are chart-only.
# ============================================================

my_indicator_name = "[Default] Swing Failure Pattern"
my_indicator_description = (
    "Causal swing-failure reversal detector with sweep and confirmation signals."
)

# @param length int 5 Swing left/right confirmation range=2:100:1
# @param bullish bool True Detect bullish swing failures
# @param bearish bool True Detect bearish swing failures
# @param swing_lines bool True Show confirmed swing levels
# @param confirm_lines bool True Show opposite confirmation levels
# @param sfp_labels bool True Show sweep and confirmation markers
# @param bull_color string #089981 Bullish color
# @param bear_color string #f23645 Bearish color
# @param validation string None Volume validation mode (recorded only)
# @param percent float 25.0 Allowed sweep penetration percentage range=0:100:1


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


def clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


length = clamp_int(params.get("length", 5), 5, 2, 100)
show_bullish = as_bool(params.get("bullish", True), True)
show_bearish = as_bool(params.get("bearish", True), True)
show_swing_lines = as_bool(params.get("swing_lines", True), True)
show_confirm_lines = as_bool(params.get("confirm_lines", True), True)
show_labels = as_bool(params.get("sfp_labels", True), True)
bull_color = str(params.get("bull_color", "#089981"))
bear_color = str(params.get("bear_color", "#f23645"))
validation = str(params.get("validation", "None"))
percent = clamp_float(params.get("percent", 25.0), 25.0, 0.0, 100.0)

df = df.copy()
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
open_price = pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)
n = len(close)

swing_high = np.full(n, np.nan, dtype=float)
opposite_low = np.full(n, np.nan, dtype=float)
swing_low = np.full(n, np.nan, dtype=float)
opposite_high = np.full(n, np.nan, dtype=float)
bull_sweep = np.full(n, np.nan, dtype=float)
bear_sweep = np.full(n, np.nan, dtype=float)
long_signal = np.full(n, np.nan, dtype=float)
short_signal = np.full(n, np.nan, dtype=float)

latest_high = None
latest_low = None
pending_bull = None
pending_bear = None

for i in range(n):
    pivot_index = i - length
    if pivot_index >= length:
        left_high = high[pivot_index - length:pivot_index]
        right_high = high[pivot_index + 1:i + 1]
        left_low = low[pivot_index - length:pivot_index]
        right_low = low[pivot_index + 1:i + 1]
        if (
            np.isfinite(high[pivot_index])
            and np.all(np.isfinite(left_high))
            and np.all(np.isfinite(right_high))
            and high[pivot_index] > np.max(left_high)
            and high[pivot_index] >= np.max(right_high)
        ):
            latest_high = {
                "level": float(high[pivot_index]),
                "opposite": float(low[pivot_index]),
                "index": pivot_index,
            }
            pending_bear = None
        if (
            np.isfinite(low[pivot_index])
            and np.all(np.isfinite(left_low))
            and np.all(np.isfinite(right_low))
            and low[pivot_index] < np.min(left_low)
            and low[pivot_index] <= np.min(right_low)
        ):
            latest_low = {
                "level": float(low[pivot_index]),
                "opposite": float(high[pivot_index]),
                "index": pivot_index,
            }
            pending_bull = None

    # A bearish SFP sweeps a confirmed swing high, then closes back below it.
    if show_bearish and latest_high is not None and pending_bear is None:
        level = latest_high["level"]
        penetration_limit = abs(level - latest_high["opposite"]) * (percent / 100.0)
        swept = high[i] > level and high[i] <= level + penetration_limit if penetration_limit else high[i] > level
        recovered = close[i] < level and open_price[i] <= level
        if swept and recovered:
            pending_bear = {"level": level, "index": i}
            if show_labels:
                bear_sweep[i] = high[i]

    # A bullish SFP sweeps a confirmed swing low, then closes back above it.
    if show_bullish and latest_low is not None and pending_bull is None:
        level = latest_low["level"]
        penetration_limit = abs(latest_low["opposite"] - level) * (percent / 100.0)
        swept = low[i] < level and low[i] >= level - penetration_limit if penetration_limit else low[i] < level
        recovered = close[i] > level and open_price[i] >= level
        if swept and recovered:
            pending_bull = {"level": level, "index": i}
            if show_labels:
                bull_sweep[i] = low[i]

    # The next opposite-level close is the confirmation event. Keeping the
    # pending record in local state means later bars cannot repaint the sweep.
    if pending_bear is not None and i > pending_bear["index"]:
        if close[i] < latest_high["opposite"]:
            if show_labels:
                short_signal[i] = high[i]
            pending_bear = None
        elif close[i] > pending_bear["level"]:
            pending_bear = None
    if pending_bull is not None and i > pending_bull["index"]:
        if close[i] > latest_low["opposite"]:
            if show_labels:
                long_signal[i] = low[i]
            pending_bull = None
        elif close[i] < pending_bull["level"]:
            pending_bull = None

    if show_swing_lines:
        if latest_high is not None:
            swing_high[i] = latest_high["level"]
        if latest_low is not None:
            swing_low[i] = latest_low["level"]
    if show_confirm_lines:
        if latest_high is not None:
            opposite_low[i] = latest_high["opposite"]
        if latest_low is not None:
            opposite_high[i] = latest_low["opposite"]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Swing High", "data": plot_list(swing_high), "color": bear_color, "overlay": True},
        {"name": "Opposite Low", "data": plot_list(opposite_low), "color": bull_color, "overlay": True},
        {"name": "Swing Low", "data": plot_list(swing_low), "color": bull_color, "overlay": True},
        {"name": "Opposite High", "data": plot_list(opposite_high), "color": bear_color, "overlay": True},
        {"name": "Bullish Sweep", "data": plot_list(bull_sweep), "color": bull_color, "overlay": True},
        {"name": "Bearish Sweep", "data": plot_list(bear_sweep), "color": bear_color, "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "SFP Confirm", "data": plot_list(long_signal), "color": bull_color},
        {"type": "sell", "text": "SFP Confirm", "data": plot_list(short_signal), "color": bear_color},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "length": length,
        "validation": validation,
        "percent": percent,
    },
}
