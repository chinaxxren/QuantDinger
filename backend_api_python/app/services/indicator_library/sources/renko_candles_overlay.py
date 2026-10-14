# ============================================================
# [Default] Renko Candles Overlay
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal Renko-style candles.  Each bar only updates the latest brick from
# the current close and a brick size known at that bar; no future bars are
# used and completed bricks are never back-filled into earlier observations.
# ============================================================

my_indicator_name = "[Default] Renko Candles Overlay"
my_indicator_description = "Causal Renko-style candle overlay calculated from OHLC data."

# @param brick_mode str ATR Brick size mode choices=Fixed,ATR
# @param brick_size float 1.0 Fixed brick size range=0.000001:1000000:0.000001
# @param atr_period int 14 ATR period range=2:200:1
# @param atr_multiplier float 1.0 ATR multiplier range=0.1:10.0:0.1

brick_mode = str(params.get("brick_mode", "Fixed")).strip().lower()
brick_size = max(1e-9, float(params.get("brick_size", 1.0)))
atr_period = max(2, int(params.get("atr_period", 14)))
atr_multiplier = max(0.1, float(params.get("atr_multiplier", 1.0)))

_df = df.copy()
close_series = _df["close"].astype(float)
high_series = _df["high"].astype(float)
low_series = _df["low"].astype(float)
close_values = close_series.to_numpy(dtype=float)
high_values = high_series.to_numpy(dtype=float)
low_values = low_series.to_numpy(dtype=float)
n = len(_df)

# Wilder-style ATR, with a fixed-size fallback until enough observations exist.
previous_close = close_series.shift(1)
true_range = pd.concat(
    [
        high_series - low_series,
        (high_series - previous_close).abs(),
        (low_series - previous_close).abs(),
    ],
    axis=1,
).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
atr_values = atr.to_numpy(dtype=float)

brick_sizes = np.full(n, brick_size, dtype=float)
if brick_mode in ("atr", "atr brick", "atr_brick"):
    for i in range(n):
        if np.isfinite(atr_values[i]) and atr_values[i] > 0.0:
            brick_sizes[i] = max(1e-9, float(atr_values[i]) * atr_multiplier)

renko_open = np.full(n, np.nan, dtype=float)
renko_high = np.full(n, np.nan, dtype=float)
renko_low = np.full(n, np.nan, dtype=float)
renko_close = np.full(n, np.nan, dtype=float)
direction = np.zeros(n, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)

anchor = np.nan
last_open = np.nan
last_close = np.nan
last_direction = 0.0

for i in range(n):
    price = close_values[i]
    size = brick_sizes[i]
    if not np.isfinite(price) or not np.isfinite(size) or size <= 0.0:
        if i > 0:
            renko_open[i] = renko_open[i - 1]
            renko_high[i] = renko_high[i - 1]
            renko_low[i] = renko_low[i - 1]
            renko_close[i] = renko_close[i - 1]
            direction[i] = direction[i - 1]
        continue

    if not np.isfinite(anchor):
        anchor = price
        last_open = price
        last_close = price
        renko_open[i] = price
        renko_high[i] = price
        renko_low[i] = price
        renko_close[i] = price
        continue

    # Build every brick crossed by the current close.  The state is retained
    # between source bars, so a later bar cannot alter an earlier output.
    previous_direction = last_direction
    delta = price - anchor
    if abs(delta) >= size:
        steps = int(abs(delta) // size)
        # Protect the worker from malformed prices while preserving the normal
        # multi-brick behavior for ordinary market data.
        steps = min(steps, 10000)
        sign = 1.0 if delta > 0.0 else -1.0
        for _ in range(steps):
            last_open = anchor
            anchor = anchor + sign * size
            last_close = anchor
            last_direction = sign

        if previous_direction != 0.0 and last_direction != previous_direction:
            if last_direction > 0.0:
                long_signal[i] = True
            else:
                short_signal[i] = True

    renko_open[i] = last_open
    renko_close[i] = last_close
    renko_high[i] = max(last_open, last_close)
    renko_low[i] = min(last_open, last_close)
    direction[i] = last_direction


def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

long_marks = [
    float(low_values[i]) if long_signal[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) if short_signal[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Renko Open", "data": _plot_list(renko_open), "color": "#90A4AE", "overlay": True},
        {"name": "Renko High", "data": _plot_list(renko_high), "color": "#26A69A", "overlay": True},
        {"name": "Renko Low", "data": _plot_list(renko_low), "color": "#EF5350", "overlay": True},
        {"name": "Renko Close", "data": _plot_list(renko_close), "color": "#42A5F5", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Renko Up", "data": long_marks, "color": "#00C853"},
        {"type": "sell", "text": "Renko Down", "data": short_marks, "color": "#FF1744"},
    ],
    "metadata": {
        "brick_mode": "ATR" if brick_mode in ("atr", "atr brick", "atr_brick") else "Fixed",
        "brick_size": _plot_list(brick_sizes),
        "direction": [int(value) for value in direction],
        "causal": True,
        "chart_only": True,
    },
    "layers": [],
}
