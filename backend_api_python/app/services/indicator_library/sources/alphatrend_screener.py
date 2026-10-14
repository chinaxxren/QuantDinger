# ============================================================
# [Default] AlphaTrend - Screener
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal AlphaTrend approximation using ATR plus RSI/MFI momentum gating.
# The screener concept is represented by chart trend state and markers because
# the frontend indicator protocol renders chart series rather than tables.
# ============================================================

my_indicator_name = "[Default] AlphaTrend - Screener"
my_indicator_description = "ATR and momentum gated AlphaTrend line with causal crossover markers."

# @param coeff float 1.0 ATR coefficient range=0.1:10.0:0.1
# @param period int 14 ATR and momentum period range=2:200:1
# @param use_mfi bool True Use MFI when volume is available
# @param show_signal bool True Show delayed signal line

coeff = max(0.1, float(params.get("coeff", 1.0)))
period = max(2, int(params.get("period", 14)))
use_mfi_value = params.get("use_mfi", True)
use_mfi = not (str(use_mfi_value).strip().lower() in ("false", "0", "no", "off"))
show_signal_value = params.get("show_signal", True)
show_signal = not (str(show_signal_value).strip().lower() in ("false", "0", "no", "off"))

_df = df.copy()
high = _df["high"].astype(float)
low = _df["low"].astype(float)
close = _df["close"].astype(float)
volume = _df["volume"].astype(float)
close_values = close.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
volume_values = volume.to_numpy(dtype=float)
n = len(_df)

previous_close = close.shift(1)
true_range = pd.concat(
    [
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ],
    axis=1,
).max(axis=1)
atr = true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().to_numpy(dtype=float)

change = close.diff()
gain = change.clip(lower=0.0).rolling(period, min_periods=period).mean().to_numpy(dtype=float)
loss = (-change.clip(upper=0.0)).rolling(period, min_periods=period).mean().to_numpy(dtype=float)
rsi = np.full(n, np.nan, dtype=float)
valid_rsi = np.isfinite(gain) & np.isfinite(loss)
rsi[valid_rsi & (loss <= 0.0) & (gain > 0.0)] = 100.0
rsi[valid_rsi & (loss <= 0.0) & (gain <= 0.0)] = 50.0
normal_rsi = valid_rsi & (loss > 0.0)
rsi[normal_rsi] = 100.0 - 100.0 / (1.0 + gain[normal_rsi] / loss[normal_rsi])

typical_price = (high + low + close) / 3.0
money_flow = typical_price * volume
price_delta = typical_price.diff().to_numpy(dtype=float)
money_flow_values = money_flow.to_numpy(dtype=float)
positive_flow = np.where(price_delta > 0.0, money_flow_values, 0.0)
negative_flow = np.where(price_delta < 0.0, money_flow_values, 0.0)
positive_sum = pd.Series(positive_flow, index=_df.index).rolling(period, min_periods=period).sum().to_numpy(dtype=float)
negative_sum = pd.Series(negative_flow, index=_df.index).rolling(period, min_periods=period).sum().to_numpy(dtype=float)
mfi = np.full(n, np.nan, dtype=float)
valid_mfi = np.isfinite(positive_sum) & np.isfinite(negative_sum)
mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum > 0.0)] = 100.0
mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum <= 0.0)] = 50.0
normal_mfi = valid_mfi & (negative_sum > 0.0)
mfi[normal_mfi] = 100.0 - 100.0 / (1.0 + positive_sum[normal_mfi] / negative_sum[normal_mfi])

momentum = mfi if use_mfi and np.isfinite(volume_values).any() and np.nanmax(np.abs(volume_values)) > 0.0 else rsi
up_level = low_values - coeff * atr
down_level = high_values + coeff * atr
alpha = np.full(n, np.nan, dtype=float)
trend = np.zeros(n, dtype=float)
for i in range(n):
    if not np.isfinite(close_values[i]):
        continue
    if i == 0 or not np.isfinite(alpha[i - 1]):
        alpha[i] = close_values[i]
    else:
        momentum_value = momentum[i]
        if np.isfinite(momentum_value) and momentum_value >= 50.0:
            candidate = up_level[i]
            alpha[i] = max(alpha[i - 1], candidate) if np.isfinite(candidate) else alpha[i - 1]
        elif np.isfinite(momentum_value):
            candidate = down_level[i]
            alpha[i] = min(alpha[i - 1], candidate) if np.isfinite(candidate) else alpha[i - 1]
        else:
            alpha[i] = alpha[i - 1]

    if i > 0 and np.isfinite(alpha[i - 1]):
        if alpha[i] > alpha[i - 1]:
            trend[i] = 1.0
        elif alpha[i] < alpha[i - 1]:
            trend[i] = -1.0
        else:
            trend[i] = trend[i - 1]

signal = np.full(n, np.nan, dtype=float)
if n > 2:
    signal[2:] = alpha[:-2]
if not show_signal:
    signal = np.full(n, np.nan, dtype=float)

long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
for i in range(1, n):
    if np.isfinite(alpha[i]) and np.isfinite(signal[i]) and np.isfinite(alpha[i - 1]) and np.isfinite(signal[i - 1]):
        long_signal[i] = alpha[i] > signal[i] and alpha[i - 1] <= signal[i - 1]
        short_signal[i] = alpha[i] < signal[i] and alpha[i - 1] >= signal[i - 1]


def plot_list(values):
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
        {"name": "AlphaTrend", "data": plot_list(alpha), "color": "#00BFA5", "overlay": True},
        {"name": "AlphaTrend Signal", "data": plot_list(signal), "color": "#FFAB00", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "AlphaTrend Up", "data": long_marks, "color": "#00C853"},
        {"type": "sell", "text": "AlphaTrend Down", "data": short_marks, "color": "#FF1744"},
    ],
    "metadata": {
        "trend": [int(value) for value in trend],
        "rsi": plot_list(rsi),
        "mfi": plot_list(mfi),
        "momentum_source": "mfi" if use_mfi and np.isfinite(volume_values).any() and np.nanmax(np.abs(volume_values)) > 0.0 else "rsi",
        "show_signal": show_signal,
        "causal": True,
        "chart_only": True,
    },
    "layers": [],
}
