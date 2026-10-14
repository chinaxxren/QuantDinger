# ============================================================
# [Default] RMI Trend Sniper
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# RMI (RSI/MFI average) trend state with an amplitude-weighted moving average
# channel. Signals are visual only and are emitted on the transition bar.
# ============================================================

my_indicator_name = "[Default] RMI Trend Sniper"
my_indicator_description = "RMI and EMA-confirmed trend channel with chart-only reversal markers."

# @param length int 14 RMI RSI/MFI length range=2:100:1
# @param pmom float 66 Positive momentum threshold range=50:100:1
# @param nmom float 30 Negative momentum threshold range=0:50:1
# @param filleshow bool true Show trend channel lines


def _clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _as_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() not in ("0", "false", "no", "off", "")


def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


length = _clamp_int(params.get("length", 14), 14, 2, 100)
pmom = _clamp_float(params.get("pmom", 66), 66.0, 50.0, 100.0)
nmom = _clamp_float(params.get("nmom", 30), 30.0, 0.0, 50.0)
filleshow = _as_bool(params.get("filleshow", True), True)

df = df.copy()
open_values = df["open"].astype(float).to_numpy()
high_values = df["high"].astype(float).to_numpy()
low_values = df["low"].astype(float).to_numpy()
close_series = df["close"].astype(float)
close_values = close_series.to_numpy()
volume_series = df["volume"].astype(float)
n = len(df)

# Wilder-style RSI using causal exponentially smoothed gains and losses.
change = close_series.diff()
gain = change.clip(lower=0.0)
loss = (-change).clip(lower=0.0)
up = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
down = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
up_values = up.to_numpy(dtype=float)
down_values = down.to_numpy(dtype=float)
rsi = np.full(n, np.nan, dtype=float)
valid_rsi = np.isfinite(up_values) & np.isfinite(down_values)
rsi[valid_rsi & (down_values <= 0.0) & (up_values > 0.0)] = 100.0
rsi[valid_rsi & (up_values <= 0.0) & (down_values > 0.0)] = 0.0
both_zero = valid_rsi & (up_values <= 0.0) & (down_values <= 0.0)
rsi[both_zero] = 50.0
normal_rsi = valid_rsi & (down_values > 0.0) & (up_values > 0.0)
rsi[normal_rsi] = 100.0 - 100.0 / (1.0 + up_values[normal_rsi] / down_values[normal_rsi])

# Money Flow Index over hlc3, matching the RMI source's input series.
typical = (df["high"].astype(float) + df["low"].astype(float) + close_series) / 3.0
money_flow = typical * volume_series
flow_change = typical.diff().to_numpy(dtype=float)
flow_values = money_flow.to_numpy(dtype=float)
positive_flow = np.where(flow_change > 0.0, flow_values, 0.0)
negative_flow = np.where(flow_change < 0.0, flow_values, 0.0)
positive_sum = pd.Series(positive_flow, index=df.index).rolling(
    length, min_periods=length
).sum().to_numpy(dtype=float)
negative_sum = pd.Series(negative_flow, index=df.index).rolling(
    length, min_periods=length
).sum().to_numpy(dtype=float)
mfi = np.full(n, np.nan, dtype=float)
valid_mfi = np.isfinite(positive_sum) & np.isfinite(negative_sum)
mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum > 0.0)] = 100.0
mfi[valid_mfi & (positive_sum <= 0.0) & (negative_sum > 0.0)] = 0.0
mfi[valid_mfi & (positive_sum <= 0.0) & (negative_sum <= 0.0)] = 50.0
normal_mfi = valid_mfi & (positive_sum > 0.0) & (negative_sum > 0.0)
mfi[normal_mfi] = 100.0 - 100.0 / (
    1.0 + positive_sum[normal_mfi] / negative_sum[normal_mfi]
)
rsi_mfi = (rsi + mfi) / 2.0

# EMA direction is the second confirmation for momentum transitions.
ema5 = close_series.ewm(span=5, adjust=False, min_periods=5).mean().to_numpy(dtype=float)
ema_change = np.full(n, np.nan, dtype=float)
if n > 1:
    ema_change[1:] = ema5[1:] - ema5[:-1]

positive = np.zeros(n, dtype=bool)
negative = np.zeros(n, dtype=bool)
trend = np.zeros(n, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
for i in range(n):
    previous_rmi = rsi_mfi[i - 1] if i > 0 else np.nan
    p_mom = (
        np.isfinite(previous_rmi)
        and np.isfinite(rsi_mfi[i])
        and np.isfinite(ema_change[i])
        and previous_rmi < pmom
        and rsi_mfi[i] > pmom
        and rsi_mfi[i] > nmom
        and ema_change[i] > 0.0
    )
    n_mom = (
        np.isfinite(rsi_mfi[i])
        and np.isfinite(ema_change[i])
        and rsi_mfi[i] < nmom
        and ema_change[i] < 0.0
    )
    if p_mom:
        positive[i] = True
        negative[i] = False
        long_signal[i] = True
    elif n_mom:
        positive[i] = False
        negative[i] = True
        short_signal[i] = True
    elif i > 0:
        positive[i] = positive[i - 1]
        negative[i] = negative[i - 1]
    trend[i] = 1.0 if positive[i] else (-1.0 if negative[i] else 0.0)

# ATR-derived bandwidth. The 20-bar offset is deliberately a past-value
# lookup, so adding future candles cannot change an earlier output.
previous_close = close_series.shift(1)
true_range = pd.concat(
    [
        df["high"].astype(float) - df["low"].astype(float),
        (df["high"].astype(float) - previous_close).abs(),
        (df["low"].astype(float) - previous_close).abs(),
    ],
    axis=1,
).max(axis=1)
atr = true_range.ewm(alpha=1.0 / 30.0, adjust=False, min_periods=30).mean()
band_source = np.minimum(atr.to_numpy(dtype=float) * 0.3, close_values * 0.003)
band = band_source.copy()
if n > 0:
    band = pd.Series(band_source, index=df.index).shift(20).to_numpy(dtype=float) / 2.0 * 8.0

# Range-weighted moving average (RWMA).
price_range = (df["high"].astype(float) - df["low"].astype(float)).clip(lower=0.0)
weighted_close = close_series * price_range
range_sum = price_range.rolling(20, min_periods=20).sum().to_numpy(dtype=float)
weighted_sum = weighted_close.rolling(20, min_periods=20).sum().to_numpy(dtype=float)
rwma = np.full(n, np.nan, dtype=float)
valid_rwma = np.isfinite(range_sum) & np.isfinite(weighted_sum) & (range_sum > 0.0)
rwma[valid_rwma] = weighted_sum[valid_rwma] / range_sum[valid_rwma]

rwma_up = np.where(positive, rwma - band, np.nan)
rwma_dn = np.where(negative, rwma + band, np.nan)
bmax_up = rwma_up + band
bmin_up = rwma_up - band
bmax_dn = rwma_dn + band
bmin_dn = rwma_dn - band

if not filleshow:
    rwma_up = np.full(n, np.nan, dtype=float)
    rwma_dn = np.full(n, np.nan, dtype=float)
    bmax_up = np.full(n, np.nan, dtype=float)
    bmin_up = np.full(n, np.nan, dtype=float)
    bmax_dn = np.full(n, np.nan, dtype=float)
    bmin_dn = np.full(n, np.nan, dtype=float)

long_marks = [
    float(low_values[i]) * 0.995 if long_signal[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) * 1.005 if short_signal[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RWMA Up", "data": _plot_list(rwma_up), "color": "#00BCD4", "overlay": True},
        {"name": "RWMA Down", "data": _plot_list(rwma_dn), "color": "#FF5252", "overlay": True},
        {"name": "Upper Up Band", "data": _plot_list(bmax_up), "color": "#80DEEA", "overlay": True},
        {"name": "Lower Up Band", "data": _plot_list(bmin_up), "color": "#80DEEA", "overlay": True},
        {"name": "Upper Down Band", "data": _plot_list(bmax_dn), "color": "#EF9A9A", "overlay": True},
        {"name": "Lower Down Band", "data": _plot_list(bmin_dn), "color": "#EF9A9A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "RMI+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "RMI-", "data": short_marks, "color": "#FF5252"},
    ],
    "metadata": {
        "rmi": _plot_list(rsi_mfi),
        "rsi_mfi": _plot_list(rsi_mfi),
        "trend": [int(value) for value in trend],
        "rwma": _plot_list(rwma),
        "band": _plot_list(band),
        "filleshow": filleshow,
        "causal": True,
        "chart_only": True,
        "params": {"length": length, "pmom": pmom, "nmom": nmom},
    },
    "layers": [],
}
