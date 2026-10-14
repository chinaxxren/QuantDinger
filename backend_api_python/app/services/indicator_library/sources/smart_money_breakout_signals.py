# ============================================================
# [Default] Smart Money Breakout Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal structure-break detector.  Reference highs/lows are taken from bars
# strictly before the current bar, so a breakout marker cannot repaint history.
# ============================================================

my_indicator_name = "[Default] Smart Money Breakout Signals"
my_indicator_description = "Causal market-structure breakouts confirmed by candle body and relative volume."

# @param swing_length int 5 Swing lookback range=2:100:1
# @param volume_length int 20 Relative-volume lookback range=2:200:1
# @param volume_multiplier float 1.0 Minimum relative-volume multiplier range=0.1:10.0:0.1
# @param use_volume bool True Require volume confirmation
# @param show_levels bool True Show active structure levels

swing_length = max(2, int(params.get("swing_length", 5)))
volume_length = max(2, int(params.get("volume_length", 20)))
volume_multiplier = max(0.1, float(params.get("volume_multiplier", 1.0)))
use_volume_value = params.get("use_volume", True)
use_volume = not (str(use_volume_value).strip().lower() in ("false", "0", "no", "off"))
show_levels_value = params.get("show_levels", True)
show_levels = not (str(show_levels_value).strip().lower() in ("false", "0", "no", "off"))

_df = df.copy()
open_values = _df["open"].astype(float).to_numpy(dtype=float)
high_values = _df["high"].astype(float).to_numpy(dtype=float)
low_values = _df["low"].astype(float).to_numpy(dtype=float)
close_values = _df["close"].astype(float).to_numpy(dtype=float)
volume_values = _df["volume"].astype(float).to_numpy(dtype=float)
n = len(_df)

prior_high = _df["high"].astype(float).shift(1).rolling(
    swing_length, min_periods=swing_length
).max().to_numpy(dtype=float)
prior_low = _df["low"].astype(float).shift(1).rolling(
    swing_length, min_periods=swing_length
).min().to_numpy(dtype=float)
average_volume = _df["volume"].astype(float).shift(1).rolling(
    volume_length, min_periods=volume_length
).mean().to_numpy(dtype=float)

structure_high = np.full(n, np.nan, dtype=float)
structure_low = np.full(n, np.nan, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
break_direction = np.zeros(n, dtype=float)

active_high = np.nan
active_low = np.nan
for i in range(n):
    if np.isfinite(prior_high[i]):
        active_high = prior_high[i]
    if np.isfinite(prior_low[i]):
        active_low = prior_low[i]

    structure_high[i] = active_high
    structure_low[i] = active_low

    volume_ok = True
    if use_volume:
        volume_ok = (
            np.isfinite(volume_values[i])
            and np.isfinite(average_volume[i])
            and volume_values[i] >= average_volume[i] * volume_multiplier
        )
    bullish_body = np.isfinite(open_values[i]) and np.isfinite(close_values[i]) and close_values[i] > open_values[i]
    bearish_body = np.isfinite(open_values[i]) and np.isfinite(close_values[i]) and close_values[i] < open_values[i]

    broke_up = (
        bullish_body
        and volume_ok
        and np.isfinite(active_high)
        and np.isfinite(close_values[i])
        and close_values[i] > active_high
        and (i == 0 or not np.isfinite(close_values[i - 1]) or close_values[i - 1] <= active_high)
    )
    broke_down = (
        bearish_body
        and volume_ok
        and np.isfinite(active_low)
        and np.isfinite(close_values[i])
        and close_values[i] < active_low
        and (i == 0 or not np.isfinite(close_values[i - 1]) or close_values[i - 1] >= active_low)
    )
    if broke_up:
        long_signal[i] = True
        break_direction[i] = 1.0
    elif broke_down:
        short_signal[i] = True
        break_direction[i] = -1.0

if not show_levels:
    structure_high = np.full(n, np.nan, dtype=float)
    structure_low = np.full(n, np.nan, dtype=float)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

long_marks = [
    float(low_values[i]) if long_signal[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) if short_signal[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Structure High", "data": plot_list(structure_high), "color": "#EF5350", "overlay": True},
        {"name": "Structure Low", "data": plot_list(structure_low), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Bullish BOS", "data": long_marks, "color": "#00C853"},
        {"type": "sell", "text": "Bearish BOS", "data": short_marks, "color": "#FF1744"},
    ],
    "metadata": {
        "break_direction": [int(value) for value in break_direction],
        "use_volume": use_volume,
        "show_levels": show_levels,
        "causal": True,
        "chart_only": True,
    },
    "layers": [],
}
