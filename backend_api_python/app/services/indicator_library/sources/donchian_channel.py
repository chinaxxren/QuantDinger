# ============================================================
# [Default] Donchian Channel
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Prior-bar rolling extremes avoid including the current candle in the
# breakout threshold. Markers are visual annotations only.
# ============================================================

my_indicator_name = "[Default] Donchian Channel"
my_indicator_description = "Prior-period high/low channel with a midpoint and breakout markers."

# @param length int 20 Channel lookback period range=5:100:1

length = max(2, int(params.get("length", 20)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
n = len(df)
upper = high.rolling(length, min_periods=length).max().shift(1)
lower = low.rolling(length, min_periods=length).min().shift(1)
mid = (upper + lower) / 2.0
cl = close.to_numpy()
up = upper.to_numpy()
lo = lower.to_numpy()
long_condition = cl > up
short_condition = cl < lo
long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])
short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Donchian Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},
        {"name": "Donchian Mid", "data": plot_list(mid), "color": "#90A4AE", "overlay": True},
        {"name": "Donchian Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "DC+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "DC-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
