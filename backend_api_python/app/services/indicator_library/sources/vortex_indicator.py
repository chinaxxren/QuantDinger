# ============================================================
# [Default] Vortex Indicator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Compares directional movement between the current high/low and prior low/high
# with true range over a trailing window. The current bar is never future data.
# ============================================================

my_indicator_name = "[Default] Vortex Indicator"
my_indicator_description = "Positive and negative directional movement ratios over true range."

# @param period int 14 Rolling calculation period range=2:200:1

period = max(2, int(params.get("period", 14)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
previous_high = high.shift(1)
previous_low = low.shift(1)
previous_close = close.shift(1)
positive_movement = (high - previous_low).abs()
negative_movement = (low - previous_high).abs()
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
positive_sum = positive_movement.rolling(period, min_periods=period).sum()
negative_sum = negative_movement.rolling(period, min_periods=period).sum()
range_sum = true_range.rolling(period, min_periods=period).sum().replace(0.0, np.nan)
vortex_positive = positive_sum / range_sum
vortex_negative = negative_sum / range_sum

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "VI+", "data": plot_list(vortex_positive), "color": "#26A69A", "overlay": False},
        {"name": "VI-", "data": plot_list(vortex_negative), "color": "#EF5350", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
