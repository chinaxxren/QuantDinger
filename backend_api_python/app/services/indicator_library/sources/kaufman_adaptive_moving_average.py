# ============================================================
# [Default] Kaufman Adaptive Moving Average
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# KAMA adapts its smoothing constant to the ratio of net price movement to
# total path movement. The recursive calculation is strictly causal.
# ============================================================

my_indicator_name = "[Default] Kaufman Adaptive Moving Average"
my_indicator_description = "An adaptive moving average that responds to directional efficiency."

# @param period int 10 Efficiency-ratio lookback period range=2:100:1
# @param fast_period int 2 Fast EMA-equivalent period range=1:50:1
# @param slow_period int 30 Slow EMA-equivalent period range=2:200:1

period = max(2, int(params.get("period", 10)))
fast_period = max(1, int(params.get("fast_period", 2)))
slow_period = max(2, int(params.get("slow_period", 30)))
if fast_period >= slow_period:
    raise ValueError("fast_period must be less than slow_period")

df = df.copy()
close = df["close"].astype(float)
change = close.diff(period).abs()
volatility = close.diff().abs().rolling(period, min_periods=period).sum()
efficiency = (change / volatility.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
fast_sc = 2.0 / (fast_period + 1.0)
slow_sc = 2.0 / (slow_period + 1.0)
smoothing = (efficiency * (fast_sc - slow_sc) + slow_sc) ** 2
kama = pd.Series(np.nan, index=close.index, dtype=float)
first_valid = period
if len(close) > first_valid:
    kama.iloc[first_valid] = close.iloc[first_valid]
    for i in range(first_valid + 1, len(close)):
        kama.iloc[i] = kama.iloc[i - 1] + smoothing.iloc[i] * (close.iloc[i] - kama.iloc[i - 1])

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "KAMA", "data": plot_list(kama), "color": "#AB47BC", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
