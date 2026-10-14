# ============================================================
# [Default] Aroon Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Measures how recently rolling highs and lows occurred. The rolling window
# includes the current bar and does not use future data.
# ============================================================

my_indicator_name = "[Default] Aroon Oscillator"
my_indicator_description = "Aroon Up/Down lines and oscillator derived from rolling high/low recency."

# @param period int 25 Lookback period range=2:200:1

period = max(2, int(params.get("period", 25)))

df = df.copy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
aroon_up = np.full(len(df), np.nan)
aroon_down = np.full(len(df), np.nan)
for i in range(period - 1, len(df)):
    start = i - period + 1
    high_window = high[start:i + 1]
    low_window = low[start:i + 1]
    if not np.isfinite(high_window).all() or not np.isfinite(low_window).all():
        continue
    # Use the most recent occurrence when the extreme appears more than once.
    high_age = period - 1 - int(np.flatnonzero(high_window == np.max(high_window))[-1])
    low_age = period - 1 - int(np.flatnonzero(low_window == np.min(low_window))[-1])
    aroon_up[i] = 100.0 * (period - high_age) / period
    aroon_down[i] = 100.0 * (period - low_age) / period
aroon = aroon_up - aroon_down

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Aroon Up", "data": plot_list(aroon_up), "color": "#26A69A", "overlay": False},
        {"name": "Aroon Down", "data": plot_list(aroon_down), "color": "#EF5350", "overlay": False},
        {"name": "Aroon Oscillator", "data": plot_list(aroon), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
