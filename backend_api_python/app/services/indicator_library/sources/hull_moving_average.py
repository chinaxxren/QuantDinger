# ============================================================
# [Default] Hull Moving Average
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# HMA combines weighted moving averages to reduce lag while retaining a
# smooth trend line. All rolling windows are trailing and causal.
# ============================================================

my_indicator_name = "[Default] Hull Moving Average"
my_indicator_description = "Reduced-lag weighted moving average for trend visualization."

# @param period int 20 HMA lookback period range=2:200:1

period = max(2, int(params.get("period", 20)))
half_period = max(1, period // 2)
sqrt_period = max(1, int(np.sqrt(period)))

df = df.copy()
close = df["close"].astype(float)

def weighted_average(window):
    weights = np.arange(1, len(window) + 1, dtype=float)
    return float(np.dot(window, weights) / weights.sum())

wma_half = close.rolling(half_period, min_periods=half_period).apply(weighted_average, raw=True)
wma_full = close.rolling(period, min_periods=period).apply(weighted_average, raw=True)
raw_hma = 2.0 * wma_half - wma_full
hma = raw_hma.rolling(sqrt_period, min_periods=sqrt_period).apply(weighted_average, raw=True)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "HMA", "data": plot_list(hma), "color": "#FFB300", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
