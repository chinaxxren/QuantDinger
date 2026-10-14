# ============================================================
# [Default] Stochastic Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Fast %K and smoothed %D oscillator in a separate pane. No trade execution.
# ============================================================

my_indicator_name = "[Default] Stochastic Oscillator"
my_indicator_description = "Stochastic %K and %D momentum oscillator in a separate chart pane."

# @param length int 14 %K lookback period range=3:50:1
# @param smooth_k int 3 %K smoothing period range=1:20:1
# @param smooth_d int 3 %D smoothing period range=1:20:1

length = max(2, int(params.get("length", 14)))
smooth_k = max(1, int(params.get("smooth_k", 3)))
smooth_d = max(1, int(params.get("smooth_d", 3)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
lowest = low.rolling(length, min_periods=length).min()
highest = high.rolling(length, min_periods=length).max()
span = (highest - lowest).replace(0.0, np.nan)
raw_k = 100.0 * (close - lowest) / span
percent_k = raw_k.rolling(smooth_k, min_periods=smooth_k).mean()
percent_d = percent_k.rolling(smooth_d, min_periods=smooth_d).mean()

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "%K", "data": plot_list(percent_k), "color": "#2962FF", "overlay": False},
        {"name": "%D", "data": plot_list(percent_d), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
