# ============================================================
# [Default] Relative Vigor Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Compares close-open movement with the high-low range using trailing weighted
# smoothing, then computes a trailing signal line. No future bars are used.
# ============================================================

my_indicator_name = "[Default] Relative Vigor Index"
my_indicator_description = "OHLC vigor oscillator with a weighted signal line."

# @param period int 10 RVI signal period range=2:100:1

period = max(2, int(params.get("period", 10)))

df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
price_move = close - open_price
price_range = (high - low).clip(lower=0.0)
weights = np.array([1.0, 2.0, 2.0, 1.0])

def trailing_weighted_average(values):
    return float(np.dot(values, weights) / weights.sum())

smoothed_move = price_move.rolling(4, min_periods=4).apply(trailing_weighted_average, raw=True)
smoothed_range = price_range.rolling(4, min_periods=4).apply(trailing_weighted_average, raw=True)
rvi = smoothed_move / smoothed_range.replace(0.0, np.nan)
signal = rvi.rolling(period, min_periods=period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RVI", "data": plot_list(rvi), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
