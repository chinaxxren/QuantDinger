# ============================================================
# [Default] Klinger Volume Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Smooths a signed volume force derived from price trend and range. The
# cumulative range state is updated bar by bar using current and prior data.
# ============================================================

my_indicator_name = "[Default] Klinger Volume Oscillator"
my_indicator_description = "Signed volume-force oscillator with a signal line."

# @param fast_period int 34 Fast EMA period range=2:200:1
# @param slow_period int 55 Slow EMA period range=3:250:1
# @param signal_period int 13 Signal EMA period range=2:100:1

fast_period = max(2, int(params.get("fast_period", 34)))
slow_period = max(fast_period + 1, int(params.get("slow_period", 55)))
signal_period = max(2, int(params.get("signal_period", 13)))

df = df.copy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
volume = df["volume"].astype(float).clip(lower=0.0).to_numpy()
price_sum = high + low + close
bar_range = np.maximum(0.0, high - low)
force = np.full(len(df), np.nan)
previous_trend = 0.0
previous_range = 0.0
cumulative_range = 0.0
previous_price_sum = np.nan
for i in range(len(df)):
    if not np.isfinite(price_sum[i]) or not np.isfinite(bar_range[i]) or not np.isfinite(volume[i]):
        continue
    if np.isfinite(previous_price_sum):
        if price_sum[i] > previous_price_sum:
            current_trend = 1.0
        elif price_sum[i] < previous_price_sum:
            current_trend = -1.0
        else:
            current_trend = previous_trend if previous_trend != 0.0 else 1.0
        if previous_trend == 0.0 or current_trend == previous_trend:
            cumulative_range += bar_range[i]
        else:
            cumulative_range = previous_range + bar_range[i]
    else:
        current_trend = 1.0
        cumulative_range = bar_range[i]
    if cumulative_range > 0.0:
        ratio = bar_range[i] / cumulative_range
        force[i] = volume[i] * abs(2.0 * ratio - 1.0) * current_trend * 100.0
    previous_trend = current_trend
    previous_range = bar_range[i]
    previous_price_sum = price_sum[i]
volume_force = pd.Series(force, index=df.index)
fast = volume_force.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
slow = volume_force.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
kvo = fast - slow
signal = kvo.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "KVO", "data": plot_list(kvo), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
