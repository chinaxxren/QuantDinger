# ============================================================
# [Default] G Channels
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Recursive high/low channel with a causal average line. Signals are visual only.
# ============================================================

my_indicator_name = "[Default] G Channels"
my_indicator_description = "Recursive high/low channel with trend-bias midline and breakout markers."

# @param length int 100 Channel length range=20:240:5
# @param signal_mode str close Midline signal mode choices=close,channel

length = int(params.get("length", 100))
signal_mode = str(params.get("signal_mode", "close"))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
n = len(df)
cl = close.to_numpy()

upper = np.full(n, np.nan)
lower = np.full(n, np.nan)
mid = np.full(n, np.nan)

if n > 0:
    upper[0] = cl[0]
    lower[0] = cl[0]
    mid[0] = cl[0]

for i in range(1, n):
    previous_gap = (upper[i - 1] - lower[i - 1]) / max(1, length)
    upper[i] = max(cl[i], upper[i - 1]) - previous_gap
    lower[i] = min(cl[i], lower[i - 1]) + previous_gap
    if lower[i] > upper[i]:
        center = (upper[i] + lower[i]) / 2.0
        upper[i] = center
        lower[i] = center
    mid[i] = (upper[i] + lower[i]) / 2.0

if signal_mode == "channel":
    long_condition = cl > upper
    short_condition = cl < lower
else:
    long_condition = cl > mid
    short_condition = cl < mid

long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])
short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "G Upper", "data": plot_list(upper), "color": "#42A5F5", "overlay": True},
        {"name": "G Mid", "data": plot_list(mid), "color": "#FFB300", "overlay": True},
        {"name": "G Lower", "data": plot_list(lower), "color": "#42A5F5", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "G+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "G-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
