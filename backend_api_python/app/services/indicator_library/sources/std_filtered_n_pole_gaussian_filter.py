# ============================================================
# [Default] STD-Filtered N-Pole Gaussian Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal cascade of EMA poles with a standard-deviation deadband. The
# deadband suppresses small changes without centered windows or future data.
# ============================================================

my_indicator_name = "[Default] STD-Filtered N-Pole Gaussian Filter"
my_indicator_description = "Standard-deviation filtered multi-pole Gaussian-style price smoother."

# @param period int 25 Gaussian smoothing period range=2:200:1
# @param poles int 5 Number of causal smoothing poles range=1:6:1
# @param filter_period int 10 Deadband volatility lookback range=2:100:1
# @param filter_strength float 1.0 Deadband standard deviation multiplier range=0.0:5.0:0.25

period = max(2, int(params.get("period", 25)))
poles = min(6, max(1, int(params.get("poles", 5))))
filter_period = max(2, int(params.get("filter_period", 10)))
filter_strength = max(0.0, float(params.get("filter_strength", 1.0)))

df = df.copy()
source = (df["open"].astype(float) + df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 4.0
rolling_std = source.rolling(filter_period, min_periods=filter_period).std()
filtered_values = source.to_numpy(copy=True)
std_values = rolling_std.to_numpy()
for i in range(1, len(filtered_values)):
    if np.isfinite(filtered_values[i - 1]) and np.isfinite(std_values[i]):
        if abs(filtered_values[i] - filtered_values[i - 1]) < filter_strength * std_values[i]:
            filtered_values[i] = filtered_values[i - 1]
filtered = pd.Series(filtered_values, index=df.index)
for _ in range(poles):
    filtered = filtered.ewm(span=period, adjust=False, min_periods=period).mean()
final_std = filtered.rolling(filter_period, min_periods=filter_period).std()
final_values = filtered.to_numpy(copy=True)
final_std_values = final_std.to_numpy()
for i in range(1, len(final_values)):
    if np.isfinite(final_values[i - 1]) and np.isfinite(final_std_values[i]):
        if abs(final_values[i] - final_values[i - 1]) < filter_strength * final_std_values[i]:
            final_values[i] = final_values[i - 1]
previous = np.concatenate([[np.nan], final_values[:-1]])
up = np.isfinite(final_values) & np.isfinite(previous) & (final_values > previous)
down = np.isfinite(final_values) & np.isfinite(previous) & (final_values < previous)
previous_up = np.concatenate([[False], up[:-1]])
previous_down = np.concatenate([[False], down[:-1]])
buy = up & (~previous_up)
sell = down & (~previous_down)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low = df["low"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
buy_marks = [float(low[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(high[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Gaussian Filter", "data": plot_list(final_values), "color": "#2962FF", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "GF+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "GF-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
