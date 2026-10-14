# ============================================================
# [Default] WaveTrend Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# LazyBear-style ESA/deviation channel index and smoothed signal line.
# Oscillator lines are rendered in a separate pane; no trade execution.
# ============================================================

my_indicator_name = "[Default] WaveTrend Oscillator"
my_indicator_description = "ESA/deviation-based WaveTrend oscillator with signal line."

# @param channel_length int 10 Channel index smoothing period range=3:40:1
# @param average_length int 21 WaveTrend signal smoothing period range=3:80:1

channel_length = max(2, int(params.get("channel_length", 10)))
average_length = max(2, int(params.get("average_length", 21)))

df = df.copy()
ap = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
esa = ap.ewm(span=channel_length, adjust=False, min_periods=channel_length).mean()
deviation = (ap - esa).abs().ewm(span=channel_length, adjust=False, min_periods=channel_length).mean()
ci = (ap - esa) / (0.015 * deviation.replace(0.0, np.nan))
wt1 = ci.ewm(span=average_length, adjust=False, min_periods=average_length).mean()
wt2 = wt1.rolling(4, min_periods=4).mean()

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "WT1", "data": plot_list(wt1), "color": "#00BCD4", "overlay": False},
        {"name": "WT2", "data": plot_list(wt2), "color": "#FF9800", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
