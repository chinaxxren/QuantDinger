# ============================================================
# [Default] Ultimate Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Combines buying-pressure ratios over three causal lookback horizons to
# reduce timeframe sensitivity. Only current and prior OHLC values are used.
# ============================================================

my_indicator_name = "[Default] Ultimate Oscillator"
my_indicator_description = "Buying-pressure oscillator combining three lookback horizons."

# @param short_period int 7 Short buying-pressure period range=2:100:1
# @param medium_period int 14 Medium buying-pressure period range=3:150:1
# @param long_period int 28 Long buying-pressure period range=4:250:1

short_period = max(2, int(params.get("short_period", 7)))
medium_period = max(short_period + 1, int(params.get("medium_period", 14)))
long_period = max(medium_period + 1, int(params.get("long_period", 28)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
previous_close = close.shift(1)
true_low = pd.concat([low, previous_close], axis=1).min(axis=1)
true_high = pd.concat([high, previous_close], axis=1).max(axis=1)
buying_pressure = close - true_low
true_range = (true_high - true_low).clip(lower=0.0)

def buying_pressure_ratio(period):
    pressure_sum = buying_pressure.rolling(period, min_periods=period).sum()
    range_sum = true_range.rolling(period, min_periods=period).sum()
    return pressure_sum / range_sum.replace(0.0, np.nan)

short_ratio = buying_pressure_ratio(short_period)
medium_ratio = buying_pressure_ratio(medium_period)
long_ratio = buying_pressure_ratio(long_period)
oscillator = 100.0 * (4.0 * short_ratio + 2.0 * medium_ratio + long_ratio) / 7.0
oscillator = oscillator.replace([np.inf, -np.inf], np.nan).clip(0.0, 100.0)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Ultimate Oscillator", "data": plot_list(oscillator), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
