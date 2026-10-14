# ============================================================
# [Default] Schaff Trend Cycle
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Applies two rolling stochastic transforms to MACD, with recursive smoothing.
# Every rolling range is trailing and each recursive stage uses past state only.
# ============================================================

my_indicator_name = "[Default] Schaff Trend Cycle"
my_indicator_description = "Smoothed double-stochastic MACD cycle oscillator."

# @param fast_period int 23 Fast MACD EMA period range=2:150:1
# @param slow_period int 50 Slow MACD EMA period range=3:250:1
# @param cycle_period int 10 Stochastic cycle period range=2:100:1
# @param smoothing float 0.5 Recursive smoothing factor range=0.1:1.0:0.1

fast_period = max(2, int(params.get("fast_period", 23)))
slow_period = max(fast_period + 1, int(params.get("slow_period", 50)))
cycle_period = max(2, int(params.get("cycle_period", 10)))
smoothing = min(1.0, max(0.01, float(params.get("smoothing", 0.5))))

df = df.copy()
close = df["close"].astype(float)
macd = close.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean() - close.ewm(
    span=slow_period, adjust=False, min_periods=slow_period
).mean()
macd_min = macd.rolling(cycle_period, min_periods=cycle_period).min()
macd_max = macd.rolling(cycle_period, min_periods=cycle_period).max()
macd_width = macd_max - macd_min
first_raw = 100.0 * (macd - macd_min) / macd_width.replace(0.0, np.nan)
first_raw = first_raw.where(macd_width != 0.0, 50.0)
first_values = first_raw.to_numpy()
first_cycle = np.full(len(df), np.nan)
previous = 50.0
for i, value in enumerate(first_values):
    if not np.isfinite(value):
        continue
    previous = smoothing * float(value) + (1.0 - smoothing) * previous
    first_cycle[i] = previous
second_series = pd.Series(first_cycle, index=df.index)
second_min = second_series.rolling(cycle_period, min_periods=cycle_period).min()
second_max = second_series.rolling(cycle_period, min_periods=cycle_period).max()
second_width = second_max - second_min
second_raw = 100.0 * (second_series - second_min) / second_width.replace(0.0, np.nan)
second_raw = second_raw.where(second_width != 0.0, 50.0)
second_values = second_raw.to_numpy()
cycle = np.full(len(df), np.nan)
previous = 50.0
for i, value in enumerate(second_values):
    if not np.isfinite(value):
        continue
    previous = smoothing * float(value) + (1.0 - smoothing) * previous
    cycle[i] = previous

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "STC", "data": plot_list(cycle), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
