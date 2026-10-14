# ============================================================
# [Default] PMax Trend Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# EMA baseline with ATR trailing stop bands. Signals are visual markers only.
# ============================================================

my_indicator_name = "[Default] PMax Trend Filter"
my_indicator_description = "EMA baseline plus ATR trailing stop bands for PMax-style trend filtering."

# @param ma_period int 10 EMA baseline period range=5:60:1
# @param atr_period int 10 ATR period range=5:60:1
# @param atr_multiplier float 3.0 ATR multiplier range=1.0:6.0:0.25

ma_period = int(params.get("ma_period", 10))
atr_period = int(params.get("atr_period", 10))
atr_multiplier = float(params.get("atr_multiplier", 3.0))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
n = len(df)

ma = close.ewm(span=ma_period, adjust=False).mean()
prev_close = close.shift(1)
tr = pd.concat([
    high - low,
    (high - prev_close).abs(),
    (low - prev_close).abs(),
], axis=1).max(axis=1)
atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()

long_stop_basic = ma - atr_multiplier * atr
short_stop_basic = ma + atr_multiplier * atr
ma_values = ma.to_numpy()
long_basic = long_stop_basic.to_numpy()
short_basic = short_stop_basic.to_numpy()

long_stop = np.full(n, np.nan)
short_stop = np.full(n, np.nan)
pmax = np.full(n, np.nan)
direction = np.zeros(n, dtype=np.int8)

for i in range(n):
    if np.isnan(long_basic[i]) or np.isnan(short_basic[i]):
        continue

    if i == 0 or direction[i - 1] == 0 or np.isnan(long_stop[i - 1]) or np.isnan(short_stop[i - 1]):
        long_stop[i] = long_basic[i]
        short_stop[i] = short_basic[i]
        direction[i] = 1 if close.iloc[i] >= ma_values[i] else -1
        pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]
        continue

    previous_ma = ma_values[i - 1]
    long_stop[i] = max(long_basic[i], long_stop[i - 1]) if previous_ma > long_stop[i - 1] else long_basic[i]
    short_stop[i] = min(short_basic[i], short_stop[i - 1]) if previous_ma < short_stop[i - 1] else short_basic[i]

    if direction[i - 1] == -1 and ma_values[i] > short_stop[i - 1]:
        direction[i] = 1
    elif direction[i - 1] == 1 and ma_values[i] < long_stop[i - 1]:
        direction[i] = -1
    else:
        direction[i] = direction[i - 1]

    pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]

prev_direction = np.concatenate([[0], direction[:-1]])
long_edge = (direction == 1) & (prev_direction == -1)
short_edge = (direction == -1) & (prev_direction == 1)

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

pmax_up = [float(v) if (d == 1 and not pd.isna(v)) else None for v, d in zip(pmax, direction)]
pmax_down = [float(v) if (d == -1 and not pd.isna(v)) else None for v, d in zip(pmax, direction)]
long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "EMA Baseline", "data": plot_list(ma), "color": "#FFB300", "overlay": True},
        {"name": "PMax Up", "data": pmax_up, "color": "#00E676", "overlay": True},
        {"name": "PMax Down", "data": pmax_down, "color": "#FF5252", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "PX+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "PX-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
