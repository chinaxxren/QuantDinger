# ============================================================
# [Default] Trendlines with Breaks
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Swing pivots are confirmed only after `length` right-hand bars. To avoid
# lookahead and historical repainting, a confirmed pivot starts drawing at its
# confirmation bar, projected forward from the pivot using the selected slope.
# Break markers are visual only and never place trades.
# ============================================================

my_indicator_name = "[Default] Trendlines with Breaks"
my_indicator_description = "Causal swing-pivot support/resistance trendlines with chart-only breakout markers."

# @param length int 14 Swing pivot left/right confirmation and slope lookback range=2:100:1
# @param mult float 1.0 Trendline slope multiplier range=0.1:5.0:0.1
# @param calc_method string Atr Slope method: Atr, Stdev, or Linreg
# @param unique_signal bool false Emit only the first breakout for each pivot trendline

length = max(2, int(params.get("length", 14)))
mult = max(0.1, float(params.get("mult", 1.0)))
calc_method = str(params.get("calc_method", "Atr")).strip().lower()
if calc_method not in ("atr", "stdev", "linreg"):
    raise ValueError("calc_method must be Atr, Stdev, or Linreg")
unique_signal = bool(params.get("unique_signal", False))

df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
n = len(df)

previous_close = close.shift(1)
true_range = pd.concat(
    [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
    axis=1,
).max(axis=1)
if calc_method == "atr":
    per_bar_slope = true_range.rolling(length, min_periods=length).mean() * mult / length
elif calc_method == "stdev":
    per_bar_slope = close.rolling(length, min_periods=length).std(ddof=0) * mult / length
else:
    # OLS slope for x=0..length-1, calculated using only the trailing window.
    x = np.arange(length, dtype=float)
    x_centered = x - x.mean()
    denominator = float(np.dot(x_centered, x_centered))
    per_bar_slope = close.rolling(length, min_periods=length).apply(
        lambda values: float(np.dot(x_centered, values - values.mean()) / denominator),
        raw=True,
    ) * mult / 2.0

high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
close_values = close.to_numpy(dtype=float)
slope_values = per_bar_slope.to_numpy(dtype=float)
upper = np.full(n, np.nan, dtype=float)
lower = np.full(n, np.nan, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)

upper_anchor = np.nan
lower_anchor = np.nan
upper_slope = 0.0
lower_slope = 0.0
upper_active = False
lower_active = False
upper_broken = False
lower_broken = False

for i in range(n):
    pivot_index = i - length
    if pivot_index >= length:
        left_high = high_values[pivot_index - length:pivot_index]
        right_high = high_values[pivot_index + 1:i + 1]
        left_low = low_values[pivot_index - length:pivot_index]
        right_low = low_values[pivot_index + 1:i + 1]
        pivot_high = (
            np.isfinite(high_values[pivot_index])
            and np.isfinite(high_values[i])
            and high_values[pivot_index] > np.max(left_high)
            and high_values[pivot_index] > np.max(right_high)
        )
        pivot_low = (
            np.isfinite(low_values[pivot_index])
            and np.isfinite(low_values[i])
            and low_values[pivot_index] < np.min(left_low)
            and low_values[pivot_index] < np.min(right_low)
        )
        if np.isfinite(slope_values[i]):
            if pivot_high:
                upper_slope = float(slope_values[i])
                upper_anchor = float(high_values[pivot_index]) + upper_slope * length
                upper_active = True
                upper_broken = False
            if pivot_low:
                lower_slope = float(slope_values[i])
                lower_anchor = float(low_values[pivot_index]) - lower_slope * length
                lower_active = True
                lower_broken = False

    if upper_active:
        upper[i] = upper_anchor
    if lower_active:
        lower[i] = lower_anchor

    prior_close = close_values[i - 1] if i else np.nan
    if upper_active and np.isfinite(upper[i]):
        crossed_up = np.isfinite(prior_close) and prior_close <= upper[i - 1] and close_values[i] > upper[i]
        if close_values[i] > upper[i] and (not unique_signal or not upper_broken):
            # Emit a marker only on the crossing bar, not on every bar above.
            if crossed_up:
                long_signal[i] = True
                upper_broken = True
    if lower_active and np.isfinite(lower[i]):
        crossed_down = np.isfinite(prior_close) and prior_close >= lower[i - 1] and close_values[i] < lower[i]
        if close_values[i] < lower[i] and (not unique_signal or not lower_broken):
            if crossed_down:
                short_signal[i] = True
                lower_broken = True

    if upper_active:
        upper_anchor -= upper_slope
    if lower_active:
        lower_anchor += lower_slope


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Resistance Trendline", "data": plot_list(upper), "color": "#EF5350", "overlay": True},
        {"name": "Support Trendline", "data": plot_list(lower), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "TL+", "data": [float(low_values[i]) * 0.995 if value and np.isfinite(low_values[i]) else None for i, value in enumerate(long_signal)], "color": "#00E676"},
        {"type": "sell", "text": "TL-", "data": [float(high_values[i]) * 1.005 if value and np.isfinite(high_values[i]) else None for i, value in enumerate(short_signal)], "color": "#FF5252"},
    ],
    "layers": [],
}
