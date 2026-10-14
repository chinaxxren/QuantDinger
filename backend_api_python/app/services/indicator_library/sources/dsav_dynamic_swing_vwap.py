# ============================================================
# [Default] DSAV Dynamic Swing Anchored VWAP
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal swing-anchored VWAP.  Swing points are detected only from the
# trailing window, and direction changes re-anchor an EWMA VWAP to the latest
# confirmed swing.  The output is a chart line plus visual cross markers.
# ============================================================

my_indicator_name = "[Default] DSAV Dynamic Swing Anchored VWAP"
my_indicator_description = "Causal swing-anchored EWMA VWAP with optional ATR adaptation."

# @param prd int 50 Swing detection period range=5:200:1
# @param base_apt int 20 EWMA half-life range=5:300:1
# @param use_adapt bool false Adapt half-life to ATR volatility
# @param vol_bias float 10.0 ATR adaptation strength range=0.0:20.0:0.5

prd = max(5, int(params.get("prd", 50)))
base_apt = max(5, int(params.get("base_apt", 20)))
use_adapt = bool(params.get("use_adapt", False))
vol_bias = max(0.0, float(params.get("vol_bias", 10.0)))

df = df.copy()
high = df["high"].astype(float).to_numpy(copy=True)
low = df["low"].astype(float).to_numpy(copy=True)
close = df["close"].astype(float).to_numpy(copy=True)
volume = df["volume"].astype(float).to_numpy(copy=True)
n = len(close)

# A trailing highest/lowest window is causal: the current value is compared
# only with candles at or before the current index.
swing_high = np.zeros(n, dtype=bool)
swing_low = np.zeros(n, dtype=bool)
for i in range(prd - 1, n):
    high_window = high[i - prd + 1:i + 1]
    low_window = low[i - prd + 1:i + 1]
    if np.isfinite(high_window).all() and np.isfinite(low_window).all():
        swing_high[i] = high[i] >= np.max(high_window)
        swing_low[i] = low[i] <= np.min(low_window)

# Forward-filled swing values emulate Pine's persistent variables without
# looking into the future.
latest_high = np.full(n, np.nan, dtype=float)
latest_low = np.full(n, np.nan, dtype=float)
high_index = np.full(n, -1, dtype=int)
low_index = np.full(n, -1, dtype=int)
current_high = np.nan
current_low = np.nan
current_high_index = -1
current_low_index = -1
for i in range(n):
    if swing_high[i]:
        current_high = high[i]
        current_high_index = i
    if swing_low[i]:
        current_low = low[i]
        current_low_index = i
    latest_high[i] = current_high
    latest_low[i] = current_low
    high_index[i] = current_high_index
    low_index[i] = current_low_index

direction = np.where(high_index > low_index, 1.0, -1.0)

# Wilder-style ATR and its slow average provide a stable volatility ratio.
previous_close = np.concatenate(([np.nan], close[:-1]))
true_range = np.maximum(
    high - low,
    np.maximum(np.abs(high - previous_close), np.abs(low - previous_close)),
)
tr_series = pd.Series(true_range)
atr = tr_series.ewm(alpha=1.0 / 50.0, adjust=False, min_periods=1).mean().to_numpy()
atr_average = pd.Series(atr).ewm(alpha=1.0 / 50.0, adjust=False, min_periods=1).mean().to_numpy()
ratio = np.divide(atr, np.maximum(atr_average, 1e-12), out=np.ones(n), where=np.isfinite(atr))
if use_adapt:
    apt_raw = base_apt / np.power(np.maximum(ratio, 1e-12), vol_bias)
else:
    apt_raw = np.full(n, float(base_apt))
apt = np.clip(np.round(apt_raw), 5.0, 300.0)

hlc3 = (high + low + close) / 3.0
dsav = np.full(n, np.nan, dtype=float)
p_acc = 0.0
vol_acc = 0.0
log2 = np.log(2.0)
previous_direction = direction[0] if n else -1.0

for i in range(n):
    if not (np.isfinite(hlc3[i]) and np.isfinite(volume[i]) and volume[i] >= 0.0):
        if i:
            direction[i] = previous_direction
        continue

    direction_changed = i > 0 and direction[i] != previous_direction
    if direction_changed:
        anchor_index = low_index[i] if direction[i] > 0 else high_index[i]
        anchor_price = latest_low[i] if direction[i] > 0 else latest_high[i]
        if anchor_index >= 0 and anchor_index <= i and np.isfinite(anchor_price):
            # Reset at the confirmed swing and update only the current bar.
            # Do not backfill the interval from the anchor: doing so would
            # rewrite historical output when a later swing is discovered.
            p_acc = anchor_price * max(volume[anchor_index], 0.0)
            vol_acc = max(volume[anchor_index], 0.0)
        previous_direction = direction[i]
        continue

    alpha = 1.0 - np.exp(-log2 / max(float(apt[i]), 1.0))
    p_acc = (1.0 - alpha) * p_acc + alpha * hlc3[i] * volume[i]
    vol_acc = (1.0 - alpha) * vol_acc + alpha * volume[i]
    if vol_acc > 0.0:
        dsav[i] = p_acc / vol_acc
    previous_direction = direction[i]

valid = np.isfinite(close) & np.isfinite(dsav)
above = valid & (close > dsav)
below = valid & (close < dsav)
buy = above & np.concatenate(([False], below[:-1]))
sell = below & np.concatenate(([False], above[:-1]))


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [float(low[i]) * 0.995 if buy[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if sell[i] and np.isfinite(high[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "DSAV", "data": plot_list(dsav), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "DSAV+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "DSAV-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
