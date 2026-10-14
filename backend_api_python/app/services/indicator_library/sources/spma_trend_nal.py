# ============================================================
# [Default] SPMA Trend NAL
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Shock Percentile Moving Average (SPMA) with adaptive volatility
# envelopes and a causal NAL trend state. This is chart-only: signals are
# visual markers and never submit, manage, or simulate orders.
# ============================================================

my_indicator_name = "[Default] SPMA Trend NAL"
my_indicator_description = "Shock-percentile moving average with adaptive volatility bands and NAL trend signals."

# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param baseline_length int 30 SPMA EMA length range=2:200:1
# @param percentrank_lookback int 30 Shock percentile lookback range=2:200:1
# @param percentile_gate float 50.0 Shock gate percentile range=0:99:1
# @param use_asym_bands bool false Use asymmetric shock-volatility bands
# @param vol_method string MeanAD Volatility method: SD, ATR, MeanAD, MedianAD, or Quantile
# @param vol_length int 14 Volatility lookback range=2:200:1
# @param vol_multiple float 0.75 Band multiplier range=0.05:8.0:0.05
# @param quantile_pct float 90.0 Residual percentile for Quantile bands range=50:99:1
# @param use_slope_gate bool false Require positive SPMA slope for long state range=0:1:1
# @param slope_length int 10 Slope lookback range=1:100:1
# @param slope_gate float 0.5 Minimum SPMA slope percent range=-20:20:0.1

baseline_length = max(2, int(params.get("baseline_length", 30)))
percentrank_lookback = max(2, int(params.get("percentrank_lookback", 30)))
percentile_gate = float(np.clip(float(params.get("percentile_gate", 50.0)), 0.0, 99.0))
use_asym_bands = bool(params.get("use_asym_bands", False))
vol_method = str(params.get("vol_method", "MeanAD")).strip().lower()
vol_length = max(2, int(params.get("vol_length", 14)))
vol_multiple = max(0.05, float(params.get("vol_multiple", 0.75)))
quantile_pct = float(np.clip(float(params.get("quantile_pct", 90.0)), 50.0, 99.0))
use_slope_gate = bool(params.get("use_slope_gate", False))
slope_length = max(1, int(params.get("slope_length", 10)))
slope_gate = float(params.get("slope_gate", 0.5))

# Keep the input field selection explicit so malformed parameter values fall
# back to a stable price source rather than failing the chart request.
source_type = str(params.get("source", "close")).strip().lower()
df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
if source_type == "hl2":
    source = (high + low) / 2.0
elif source_type == "hlc3":
    source = (high + low + close) / 3.0
elif source_type == "ohlc4":
    source = (open_price + high + low + close) / 4.0
else:
    source = close.copy()

n = len(source)
finite_source = np.isfinite(source)

# EMA used by the SPMA gate. The EMA evolves causally on every bar, while the
# published SPMA only accepts updates when the current return is sufficiently
# unusual according to its trailing percentile rank.
ema_source = np.full(n, np.nan, dtype=float)
spma = np.full(n, np.nan, dtype=float)
alpha = 2.0 / (baseline_length + 1.0)
for i in range(n):
    if not finite_source[i]:
        if i:
            ema_source[i] = ema_source[i - 1]
            spma[i] = spma[i - 1]
        continue
    if i == 0 or not np.isfinite(ema_source[i - 1]):
        ema_source[i] = source[i]
        spma[i] = source[i]
    else:
        ema_source[i] = alpha * source[i] + (1.0 - alpha) * ema_source[i - 1]
        spma[i] = ema_source[i] if np.isfinite(spma[i - 1]) and np.isfinite(ema_source[i]) else source[i]

returns = np.full(n, np.nan, dtype=float)
if n > 1:
    returns[1:] = np.diff(source)
abs_returns = np.abs(returns)

# A trailing percentile rank of the current return. rolling.apply is used only
# for this small order-statistic operation; it does not inspect future bars.
def last_percentile(values):
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan
    return 100.0 * float(np.count_nonzero(values <= values[-1])) / float(len(values))

rank = pd.Series(returns).rolling(
    percentrank_lookback,
    min_periods=percentrank_lookback,
).apply(last_percentile, raw=True).to_numpy()
for i in range(n):
    if i == 0 or not np.isfinite(spma[i]):
        continue
    if not np.isfinite(rank[i]) or rank[i] <= percentile_gate:
        spma[i] = spma[i - 1] if i else source[i]
    else:
        spma[i] = ema_source[i]

# Wilder ATR with the same causal SMA seed used by Pine's ta.atr/RMA family.
previous_close = np.concatenate(([np.nan], close[:-1]))
true_range = np.maximum(
    high - low,
    np.maximum(np.abs(high - previous_close), np.abs(low - previous_close)),
)
true_range[~np.isfinite(true_range)] = np.nan
atr = np.full(n, np.nan, dtype=float)
atr_seed = vol_length
if n > atr_seed:
    seed = true_range[1:atr_seed + 1]
    if len(seed) == vol_length:
        atr[atr_seed] = float(np.mean(seed))
        for i in range(atr_seed + 1, n):
            if np.isfinite(true_range[i]):
                atr[i] = ((vol_length - 1.0) * atr[i - 1] + true_range[i]) / vol_length

source_series = pd.Series(source)
rolling_mean = source_series.rolling(vol_length, min_periods=vol_length).mean()
rolling_sd = source_series.rolling(vol_length, min_periods=vol_length).std(ddof=0)
mean_ad = source_series.rolling(vol_length, min_periods=vol_length).apply(
    lambda values: float(np.mean(np.abs(values - np.mean(values)))), raw=True
)
median_ad = source_series.rolling(vol_length, min_periods=vol_length).apply(
    lambda values: float(np.median(np.abs(values - np.median(values)))), raw=True
)

if vol_method == "sd":
    raw_vol = rolling_sd.to_numpy()
elif vol_method == "atr":
    raw_vol = atr
elif vol_method == "medianad":
    raw_vol = median_ad.to_numpy()
elif vol_method == "quantile":
    raw_vol = np.full(n, np.nan, dtype=float)
else:
    raw_vol = mean_ad.to_numpy()

# Quantile mode measures positive/negative SPMA residuals separately. Empty
# sides fall back to the absolute residual distribution for that window.
upper_vol = np.full(n, np.nan, dtype=float)
lower_vol = np.full(n, np.nan, dtype=float)
if vol_method == "quantile":
    residual = source - spma
    q = quantile_pct / 100.0
    for i in range(vol_length - 1, n):
        window = residual[i - vol_length + 1:i + 1]
        window = window[np.isfinite(window)]
        if len(window) == 0:
            continue
        absolute = np.abs(window)
        positive = window[window > 0.0]
        negative = -window[window < 0.0]
        upper_values = positive if len(positive) else absolute
        lower_values = negative if len(negative) else absolute
        upper_vol[i] = max(float(np.quantile(upper_values, q)), 1e-12)
        lower_vol[i] = max(float(np.quantile(lower_values, q)), 1e-12)
else:
    smoothed_vol = pd.Series(raw_vol).ewm(
        span=vol_length, adjust=False, min_periods=vol_length
    ).mean().to_numpy()
    upper_vol[:] = smoothed_vol
    lower_vol[:] = smoothed_vol

# Optional asymmetric volatility adjustment from positive/negative return
# energy. The rolling mean keeps the multiplier bounded and avoids unstable
# one-bar spikes while remaining fully causal.
if use_asym_bands and vol_method != "quantile":
    positive_energy = np.where(np.isfinite(returns) & (returns > 0.0), returns * returns, 0.0)
    negative_energy = np.where(np.isfinite(returns) & (returns < 0.0), returns * returns, 0.0)
    bull_var = pd.Series(positive_energy).ewm(span=vol_length, adjust=False, min_periods=vol_length).mean().to_numpy()
    bear_var = pd.Series(negative_energy).ewm(span=vol_length, adjust=False, min_periods=vol_length).mean().to_numpy()
    total_var = bull_var + bear_var
    bull_mult = np.full(n, np.nan, dtype=float)
    bear_mult = np.full(n, np.nan, dtype=float)
    valid = np.isfinite(total_var) & (total_var > 1e-18)
    bull_mult[valid] = 1.0 + 3.0 * (np.sqrt(2.0 * bull_var[valid] / total_var[valid]) - 1.0)
    bear_mult[valid] = 1.0 + 3.0 * (np.sqrt(2.0 * bear_var[valid] / total_var[valid]) - 1.0)
    bull_mult = pd.Series(bull_mult).rolling(180, min_periods=1).mean().to_numpy()
    bear_mult = pd.Series(bear_mult).rolling(180, min_periods=1).mean().to_numpy()
    upper_vol = upper_vol * np.clip(np.nan_to_num(bull_mult, nan=1.0), 0.1, 4.0)
    lower_vol = lower_vol * np.clip(np.nan_to_num(bear_mult, nan=1.0), 0.1, 4.0)

upper_band = spma + vol_multiple * upper_vol
lower_band = spma - vol_multiple * lower_vol

# NAL state machine: break the lower band first on a bar where both tests
# happen, matching the original sequential Pine-style state updates.
state = np.zeros(n, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
slope = np.full(n, np.nan, dtype=float)
for i in range(n):
    if i >= slope_length and np.isfinite(spma[i]) and np.isfinite(spma[i - slope_length]):
        denominator = spma[i - slope_length]
        if abs(denominator) > 1e-12:
            slope[i] = (spma[i] - denominator) / abs(denominator) * 100.0
    previous_state = state[i - 1] if i else 0.0
    state[i] = previous_state
    rising = i > 0 and np.isfinite(spma[i]) and np.isfinite(spma[i - 1]) and spma[i] > spma[i - 1]
    slope_ok = (not use_slope_gate) or (np.isfinite(slope[i]) and slope[i] >= slope_gate)
    if np.isfinite(upper_band[i]) and rising and source[i] > upper_band[i] and slope_ok:
        state[i] = 1.0
    if np.isfinite(lower_band[i]) and source[i] < lower_band[i]:
        state[i] = -1.0
    long_signal[i] = state[i] == 1.0 and previous_state != 1.0
    short_signal[i] = state[i] == -1.0 and previous_state != -1.0


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "SPMA", "data": plot_list(spma), "color": "#2962FF", "overlay": True},
        {"name": "Upper Band", "data": plot_list(upper_band), "color": "#AB47BC", "overlay": True},
        {"name": "Lower Band", "data": plot_list(lower_band), "color": "#AB47BC", "overlay": True},
        {"name": "NAL State", "data": plot_list(state), "color": "#26A69A", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "SPMA+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "SPMA-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
