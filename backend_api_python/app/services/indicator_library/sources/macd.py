# ============================================================
# [Default] MACD
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Moving Average Convergence Divergence oscillator. Values render in a
# separate pane; this indicator does not submit or manage orders.
# ============================================================

my_indicator_name = "[Default] MACD"
my_indicator_description = "MACD, signal line, and histogram shown in a separate chart pane."

# @param fast int 12 Fast EMA period range=2:50:1
# @param slow int 26 Slow EMA period range=3:100:1
# @param signal int 9 Signal EMA period range=2:50:1

fast = max(2, int(params.get("fast", 12)))
slow = max(fast + 1, int(params.get("slow", 26)))
signal_period = max(2, int(params.get("signal", 9)))

df = df.copy()
close = df["close"].astype(float)
macd_line = close.ewm(span=fast, adjust=False, min_periods=fast).mean() - close.ewm(
    span=slow, adjust=False, min_periods=slow
).mean()
signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
histogram = macd_line - signal_line

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "MACD", "data": plot_list(macd_line), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal_line), "color": "#FF6D00", "overlay": False},
        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
