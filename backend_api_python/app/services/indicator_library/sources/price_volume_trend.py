# ============================================================
# [Default] Price Volume Trend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Cumulative volume-weighted percentage price change with an optional signal
# average. Accumulation starts at zero and is strictly bar-by-bar causal.
# ============================================================

my_indicator_name = "[Default] Price Volume Trend"
my_indicator_description = "Cumulative percentage price change weighted by volume."

# @param signal_period int 21 Signal EMA period range=1:200:1

signal_period = max(1, int(params.get("signal_period", 21)))

df = df.copy()
close = df["close"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
previous_close = close.shift(1)
base = previous_close.replace(0.0, np.nan)
period_return = close.div(base).sub(1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
pvt = (period_return * volume).cumsum()
signal = pvt.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "PVT", "data": plot_list(pvt), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
