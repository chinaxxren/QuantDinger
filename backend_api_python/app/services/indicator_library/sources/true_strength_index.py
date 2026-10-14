# ============================================================
# [Default] True Strength Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Double-smoothed price momentum normalized by double-smoothed absolute
# momentum. Exponential smoothing is causal and stable as bars are appended.
# ============================================================

my_indicator_name = "[Default] True Strength Index"
my_indicator_description = "Double-smoothed, normalized momentum with a signal line."

# @param long_period int 25 Long EMA period range=2:200:1
# @param short_period int 13 Short EMA period range=2:100:1
# @param signal_period int 7 Signal EMA period range=2:100:1

long_period = max(2, int(params.get("long_period", 25)))
short_period = max(2, int(params.get("short_period", 13)))
signal_period = max(2, int(params.get("signal_period", 7)))

df = df.copy()
close = df["close"].astype(float)
momentum = close.diff()
smoothed_momentum = momentum.ewm(span=long_period, adjust=False, min_periods=long_period).mean().ewm(
    span=short_period, adjust=False, min_periods=short_period
).mean()
smoothed_absolute = momentum.abs().ewm(span=long_period, adjust=False, min_periods=long_period).mean().ewm(
    span=short_period, adjust=False, min_periods=short_period
).mean()
tsi = 100.0 * smoothed_momentum / smoothed_absolute.replace(0.0, np.nan)
tsi = tsi.replace([np.inf, -np.inf], np.nan)
signal = tsi.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "TSI", "data": plot_list(tsi), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
