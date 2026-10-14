# ============================================================
# [Default] Fisher Transform
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Maps the rolling midpoint position into a bounded recursive Fisher series.
# The rolling range includes the current bar only; no centered/future window.
# ============================================================

my_indicator_name = "[Default] Fisher Transform"
my_indicator_description = "Recursive Fisher transform of normalized rolling price position."

# @param period int 10 Rolling normalization period range=2:200:1
# @param signal_period int 1 Signal smoothing period range=1:50:1

period = max(2, int(params.get("period", 10)))
signal_period = max(1, int(params.get("signal_period", 1)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
price = (high + low) / 2.0
rolling_high = price.rolling(period, min_periods=period).max().to_numpy()
rolling_low = price.rolling(period, min_periods=period).min().to_numpy()
price_values = price.to_numpy()
normalized = np.full(len(df), np.nan)
fisher = np.full(len(df), np.nan)
previous_value = 0.0
previous_fisher = 0.0
for i in range(len(df)):
    if not np.isfinite(rolling_high[i]) or not np.isfinite(rolling_low[i]) or not np.isfinite(price_values[i]):
        continue
    width = rolling_high[i] - rolling_low[i]
    raw = 0.0 if width <= 0.0 else 2.0 * ((price_values[i] - rolling_low[i]) / width - 0.5)
    value = 0.33 * raw + 0.67 * previous_value
    value = min(0.999, max(-0.999, value))
    transformed = 0.5 * np.log((1.0 + value) / (1.0 - value)) + 0.5 * previous_fisher
    normalized[i] = value
    fisher[i] = transformed
    previous_value = value
    previous_fisher = transformed
signal = pd.Series(fisher, index=df.index).ewm(
    span=signal_period, adjust=False, min_periods=signal_period
).mean().to_numpy()

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Fisher", "data": plot_list(fisher), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
