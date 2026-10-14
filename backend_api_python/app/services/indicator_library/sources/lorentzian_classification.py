# ============================================================
# [Default] Lorentzian Classification
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal Lorentzian-distance KNN classifier inspired by the TradingView /
# MiniBT Lorentzian Classification indicator.  It is a chart-only indicator:
# all entries and exits are visual markers and never execute trades.
# ============================================================

my_indicator_name = "[Default] Lorentzian Classification"
my_indicator_description = (
    "Causal Lorentzian-distance KNN classification with technical features, "
    "filters, and kernel-regression chart signals."
)

# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param neighbors_count int 8 Number of KNN neighbors range=1:32:1
# @param max_bars_back int 2000 Maximum historical KNN window range=100:5000:100
# @param feature_count int 5 Number of features used by KNN range=1:5:1
# @param include_full_history bool false Search all available history
# @param f1_string string RSI Feature 1: RSI, WT, CCI, or ADX
# @param f1_paramA int 14 Feature 1 primary length range=2:100:1
# @param f1_paramB int 1 Feature 1 secondary length range=1:50:1
# @param f2_string string WT Feature 2: RSI, WT, CCI, or ADX
# @param f2_paramA int 10 Feature 2 primary length range=2:100:1
# @param f2_paramB int 11 Feature 2 secondary length range=1:50:1
# @param f3_string string CCI Feature 3: RSI, WT, CCI, or ADX
# @param f3_paramA int 20 Feature 3 primary length range=2:100:1
# @param f3_paramB int 1 Feature 3 secondary length range=1:50:1
# @param f4_string string ADX Feature 4: RSI, WT, CCI, or ADX
# @param f4_paramA int 20 Feature 4 primary length range=2:100:1
# @param f4_paramB int 2 Feature 4 secondary length range=1:50:1
# @param f5_string string RSI Feature 5: RSI, WT, CCI, or ADX
# @param f5_paramA int 9 Feature 5 primary length range=2:100:1
# @param f5_paramB int 1 Feature 5 secondary length range=1:50:1
# @param use_volatility_filter bool true Require ATR expansion
# @param use_regime_filter bool true Require a positive trend regime score
# @param regime_threshold float -0.1 Regime score threshold range=-1.0:2.0:0.1
# @param use_adx_filter bool false Require ADX strength
# @param adx_threshold float 20 ADX threshold range=0:100:1
# @param use_ema_filter bool false Require price/EMA alignment
# @param ema_period int 200 EMA filter period range=2:500:1
# @param use_sma_filter bool false Require price/SMA alignment
# @param sma_period int 200 SMA filter period range=2:500:1
# @param use_kernel_filter bool true Require kernel direction agreement
# @param use_kernel_smoothing bool false Use RQ/Gaussian crossover direction
# @param kernel_h int 8 Kernel lookback shape range=2:100:1
# @param kernel_r float 8.0 Rational quadratic relative weighting range=0.5:20.0:0.5
# @param kernel_x int 25 Kernel window offset range=2:100:1
# @param kernel_lag int 2 Kernel direction lag range=1:20:1
# @param use_dynamic_exits bool false Use kernel/opposite prediction exits

# Keep parameter coercion local to the source file so it remains executable by
# the indicator sandbox without importing application code.
def _as_bool(value, default):
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    if value is None:
        return default
    return bool(value)


def _ema(values, length):
    values = values.astype(float, copy=False)
    result = np.full(len(values), np.nan, dtype=float)
    if len(values) == 0:
        return result
    first = np.flatnonzero(np.isfinite(values))
    if len(first) == 0:
        return result
    start = int(first[0])
    result[start] = values[start]
    alpha = 2.0 / (float(length) + 1.0)
    for i in range(start + 1, len(values)):
        if np.isfinite(values[i]):
            result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]
        else:
            result[i] = result[i - 1]
    return result


def _rma(values, length):
    values = values.astype(float, copy=False)
    result = np.full(len(values), np.nan, dtype=float)
    if len(values) < length:
        return result
    for i in range(length - 1, len(values)):
        window = values[i - length + 1:i + 1]
        if np.all(np.isfinite(window)):
            result[i] = float(np.mean(window))
            break
    finite_seed = np.flatnonzero(np.isfinite(result))
    if len(finite_seed) == 0:
        return result
    start = int(finite_seed[0])
    for i in range(start + 1, len(values)):
        if np.isfinite(values[i]) and np.isfinite(result[i - 1]):
            result[i] = (result[i - 1] * (length - 1.0) + values[i]) / length
        else:
            result[i] = result[i - 1]
    return result


def _true_range(high, low, close):
    result = np.full(len(close), np.nan, dtype=float)
    if len(close):
        result[0] = high[0] - low[0]
    for i in range(1, len(close)):
        result[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return result


def _rsi(close, length):
    delta = np.full(len(close), np.nan, dtype=float)
    if len(close) > 1:
        delta[1:] = np.diff(close)
    gain = np.where(np.isfinite(delta) & (delta > 0.0), delta, 0.0)
    loss = np.where(np.isfinite(delta) & (delta < 0.0), -delta, 0.0)
    avg_gain = _rma(gain, length)
    avg_loss = _rma(loss, length)
    ratio = np.divide(avg_gain, avg_loss, out=np.full(len(close), np.nan), where=np.isfinite(avg_loss) & (avg_loss > 0.0))
    result = 100.0 - 100.0 / (1.0 + ratio)
    result[(avg_loss == 0.0) & (avg_gain > 0.0)] = 100.0
    result[(avg_loss == 0.0) & (avg_gain == 0.0)] = 50.0
    return result


def _cci(high, low, close, length):
    typical = (high + low + close) / 3.0
    result = np.full(len(close), np.nan, dtype=float)
    for i in range(length - 1, len(close)):
        window = typical[i - length + 1:i + 1]
        if not np.all(np.isfinite(window)):
            continue
        middle = float(np.mean(window))
        deviation = float(np.mean(np.abs(window - middle)))
        if deviation > 1e-12:
            result[i] = (typical[i] - middle) / (0.015 * deviation)
        else:
            result[i] = 0.0
    return result


def _adx(high, low, close, length):
    up = np.full(len(close), np.nan, dtype=float)
    down = np.full(len(close), np.nan, dtype=float)
    if len(close) > 1:
        up[1:] = np.diff(high)
        down[1:] = -np.diff(low)
    plus_dm = np.where((up > down) & (up > 0.0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0.0), down, 0.0)
    tr = _true_range(high, low, close)
    smooth_tr = _rma(tr, length)
    plus_di = np.divide(100.0 * _rma(plus_dm, length), smooth_tr, out=np.full(len(close), np.nan), where=np.isfinite(smooth_tr) & (smooth_tr > 0.0))
    minus_di = np.divide(100.0 * _rma(minus_dm, length), smooth_tr, out=np.full(len(close), np.nan), where=np.isfinite(smooth_tr) & (smooth_tr > 0.0))
    denominator = plus_di + minus_di
    dx = np.divide(100.0 * np.abs(plus_di - minus_di), denominator, out=np.full(len(close), np.nan), where=np.isfinite(denominator) & (denominator > 0.0))
    return _rma(dx, length)


def _wave_trend(high, low, close, length_a, length_b):
    source = (high + low + close) / 3.0
    esa = _ema(source, length_a)
    deviation = _ema(np.abs(source - esa), length_a)
    ci = np.divide(source - esa, 0.015 * deviation, out=np.full(len(close), np.nan), where=np.isfinite(deviation) & (deviation > 1e-12))
    wt = _ema(ci, length_b)
    # Bounded causal normalization; unlike a full-history min/max it cannot
    # change when new candles are appended to the right of the input.
    return 0.5 + 0.5 * np.tanh(wt / 100.0)


def _feature(name, pa, pb, high, low, close):
    name = str(name or "RSI").upper()
    pa = max(2, int(pa))
    pb = max(1, int(pb))
    if name == "WT":
        return _wave_trend(high, low, close, pa, max(1, pb))
    if name == "CCI":
        cci = _cci(high, low, close, pa)
        return 0.5 + np.arctan(cci / 100.0) / np.pi
    if name == "ADX":
        return np.clip(_adx(high, low, close, pa) / 100.0, 0.0, 1.0)
    rsi = _rsi(close, pa) / 100.0
    return np.clip(_ema(rsi, pb), 0.0, 1.0)


def _rolling_mean(values, length):
    result = np.full(len(values), np.nan, dtype=float)
    for i in range(length - 1, len(values)):
        window = values[i - length + 1:i + 1]
        if np.all(np.isfinite(window)):
            result[i] = float(np.mean(window))
    return result


df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
n = len(close)
source_name = str(params.get("source", "close")).lower()
if source_name == "hl2":
    source = (high + low) / 2.0
elif source_name == "hlc3":
    source = (high + low + close) / 3.0
elif source_name == "ohlc4":
    source = (open_price + high + low + close) / 4.0
else:
    source = close.copy()

neighbors_count = max(1, min(32, int(params.get("neighbors_count", 8))))
max_bars_back = max(100, min(5000, int(params.get("max_bars_back", 2000))))
feature_count = max(1, min(5, int(params.get("feature_count", 5))))
include_full_history = _as_bool(params.get("include_full_history", False), False)

feature_arrays = []
for feature_index in range(1, feature_count + 1):
    feature_arrays.append(
        _feature(
            params.get("f%d_string" % feature_index, "RSI"),
            params.get("f%d_paramA" % feature_index, 14),
            params.get("f%d_paramB" % feature_index, 1),
            high,
            low,
            close,
        )
    )
features = np.column_stack(feature_arrays) if feature_arrays else np.empty((n, 0), dtype=float)

# A four-bar direction label is only eligible as training data after the label
# is known.  The current bar and the latest four bars are therefore excluded
# from their own KNN search, preventing look-ahead and self-neighbor leakage.
horizon = 4
labels = np.zeros(n, dtype=float)
for i in range(horizon, n):
    if np.isfinite(source[i]) and np.isfinite(source[i - horizon]):
        labels[i] = 1.0 if source[i] > source[i - horizon] else (-1.0 if source[i] < source[i - horizon] else 0.0)

prediction = np.full(n, np.nan, dtype=float)
for i in range(n):
    if features.shape[1] == 0 or not np.all(np.isfinite(features[i])) or i <= horizon:
        continue
    end = i - horizon
    start = 0 if include_full_history else max(0, end - max_bars_back + 1)
    candidates = np.arange(start, end + 1, dtype=int)
    if len(candidates) == 0:
        continue
    # Keep the original indicator's temporal de-clustering idea while still
    # allowing the nearest-neighbor search to work on short histories.
    candidates = candidates[((i - candidates) % 4) != 0]
    if len(candidates) == 0:
        continue
    valid = np.all(np.isfinite(features[candidates]), axis=1) & np.isfinite(labels[candidates])
    candidates = candidates[valid]
    if len(candidates) == 0:
        continue
    distances = np.sum(np.log1p(np.abs(features[candidates] - features[i])), axis=1)
    order = np.argsort(distances)
    selected = order[:min(neighbors_count, len(order))]
    prediction[i] = float(np.sum(labels[candidates[selected]]))

# ATR expansion, Kaufman-style regime score, and directional filters.
true_range = _true_range(high, low, close)
atr = _rma(true_range, 14)
atr_baseline = _rolling_mean(atr, 10)
volatility_ok = np.isfinite(atr) & np.isfinite(atr_baseline) & (atr >= atr_baseline)

price_delta = np.full(n, np.nan, dtype=float)
if n > 1:
    price_delta[1:] = (high[1:] + low[1:] + close[1:]) / 3.0 - (high[:-1] + low[:-1] + close[:-1]) / 3.0
value1 = _ema(price_delta, 5)
value2 = _ema(high - low, 10)
omega = np.divide(np.abs(value1), value2, out=np.full(n, np.nan), where=np.isfinite(value2) & (value2 > 1e-12))
alpha = (-omega * omega + np.sqrt(omega ** 4 + 16.0 * omega * omega)) / 8.0
klmf = np.full(n, np.nan, dtype=float)
for i in range(n):
    if not np.isfinite(source[i]):
        continue
    if i == 0 or not np.isfinite(klmf[i - 1]):
        klmf[i] = source[i]
    else:
        adaptive_alpha = float(np.clip(alpha[i], 0.0, 1.0)) if np.isfinite(alpha[i]) else 0.0
        klmf[i] = adaptive_alpha * source[i] + (1.0 - adaptive_alpha) * klmf[i - 1]
abs_slope = np.full(n, np.nan, dtype=float)
if n > 1:
    abs_slope[1:] = np.abs(np.diff(klmf))
avg_slope = _ema(abs_slope, 200)
regime_score = np.divide(abs_slope - avg_slope, avg_slope, out=np.full(n, np.nan), where=np.isfinite(avg_slope) & (avg_slope > 1e-12))
regime_threshold = float(params.get("regime_threshold", -0.1))
regime_ok = np.isfinite(regime_score) & (regime_score >= regime_threshold)

adx_filter_period = max(2, int(params.get("f4_paramA", 20)))
adx_values = _adx(high, low, close, adx_filter_period)
adx_threshold = float(params.get("adx_threshold", 20.0))
adx_ok = np.isfinite(adx_values) & (adx_values >= adx_threshold)
ema_period = max(2, min(500, int(params.get("ema_period", 200))))
sma_period = max(2, min(500, int(params.get("sma_period", 200))))
ema_values = _ema(source, ema_period)
sma_values = _rolling_mean(source, sma_period)
use_volatility_filter = _as_bool(params.get("use_volatility_filter", True), True)
use_regime_filter = _as_bool(params.get("use_regime_filter", True), True)
use_adx_filter = _as_bool(params.get("use_adx_filter", False), False)
use_ema_filter = _as_bool(params.get("use_ema_filter", False), False)
use_sma_filter = _as_bool(params.get("use_sma_filter", False), False)

kernel_h = max(2, int(params.get("kernel_h", 8)))
kernel_r = max(0.5, float(params.get("kernel_r", 8.0)))
kernel_x = max(2, int(params.get("kernel_x", 25)))
kernel_lag = max(1, int(params.get("kernel_lag", 2)))
kernel_window = kernel_x + 2
ages = np.arange(kernel_window, dtype=float)
rq_weights = (1.0 + (ages * ages / (float(kernel_h * kernel_h) * 2.0 * kernel_r))) ** (-kernel_r)
gaussian_weights = np.exp(-(ages * ages) / (2.0 * float(kernel_h * kernel_h)))
yhat1 = np.full(n, np.nan, dtype=float)
yhat2 = np.full(n, np.nan, dtype=float)
for i in range(kernel_window - 1, n):
    window = source[i - kernel_window + 1:i + 1][::-1]
    if np.all(np.isfinite(window)):
        yhat1[i] = float(np.sum(window * rq_weights) / np.sum(rq_weights))
        yhat2[i] = float(np.sum(window * gaussian_weights) / np.sum(gaussian_weights))

use_kernel_filter = _as_bool(params.get("use_kernel_filter", True), True)
use_kernel_smoothing = _as_bool(params.get("use_kernel_smoothing", False), False)
use_dynamic_exits = _as_bool(params.get("use_dynamic_exits", False), False)
kernel_bull = np.zeros(n, dtype=bool)
kernel_bear = np.zeros(n, dtype=bool)
for i in range(n):
    lag_index = i - kernel_lag
    if not np.isfinite(yhat1[i]) or lag_index < 0:
        continue
    if use_kernel_smoothing and np.isfinite(yhat2[i]):
        kernel_bull[i] = yhat1[i] > yhat2[i]
        kernel_bear[i] = yhat1[i] < yhat2[i]
    elif np.isfinite(yhat1[lag_index]):
        kernel_bull[i] = yhat1[i] > yhat1[lag_index]
        kernel_bear[i] = yhat1[i] < yhat1[lag_index]

signal = np.zeros(n, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
exit_long = np.zeros(n, dtype=bool)
exit_short = np.zeros(n, dtype=bool)
for i in range(n):
    previous = signal[i - 1] if i else 0.0
    signal[i] = previous
    if not np.isfinite(prediction[i]) or prediction[i] == 0.0:
        continue
    common_ok = (
        (not use_volatility_filter or volatility_ok[i])
        and (not use_regime_filter or regime_ok[i])
        and (not use_adx_filter or adx_ok[i])
    )
    if prediction[i] > 0.0:
        direction_ok = (
            common_ok
            and (not use_ema_filter or (np.isfinite(ema_values[i]) and source[i] >= ema_values[i]))
            and (not use_sma_filter or (np.isfinite(sma_values[i]) and source[i] >= sma_values[i]))
        )
        if direction_ok:
            signal[i] = 1.0
    elif prediction[i] < 0.0:
        direction_ok = (
            common_ok
            and (not use_ema_filter or (np.isfinite(ema_values[i]) and source[i] <= ema_values[i]))
            and (not use_sma_filter or (np.isfinite(sma_values[i]) and source[i] <= sma_values[i]))
        )
        if direction_ok:
            signal[i] = -1.0

    long_signal[i] = signal[i] == 1.0 and previous != 1.0 and (not use_kernel_filter or kernel_bull[i])
    short_signal[i] = signal[i] == -1.0 and previous != -1.0 and (not use_kernel_filter or kernel_bear[i])
    if previous == 1.0:
        exit_long[i] = signal[i] == -1.0 or (use_dynamic_exits and kernel_bear[i] and prediction[i] <= 0.0)
    if previous == -1.0:
        exit_short[i] = signal[i] == 1.0 or (use_dynamic_exits and kernel_bull[i] and prediction[i] >= 0.0)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None for i in range(n)]
exit_long_marks = [float(high[i]) * 1.002 if exit_long[i] and np.isfinite(high[i]) else None for i in range(n)]
exit_short_marks = [float(low[i]) * 0.998 if exit_short[i] and np.isfinite(low[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Kernel Estimate", "data": plot_list(yhat1), "color": "#2962FF", "overlay": True},
        {"name": "Kernel Estimate 2", "data": plot_list(yhat2), "color": "#AB47BC", "overlay": True},
        {"name": "Prediction", "data": plot_list(prediction), "color": "#26A69A", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FFA726", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "LC Long", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "LC Short", "data": sell_marks, "color": "#FF5252"},
        {"type": "exit_long", "text": "LC Exit Long", "data": exit_long_marks, "color": "#FF9800"},
        {"type": "exit_short", "text": "LC Exit Short", "data": exit_short_marks, "color": "#26C6DA"},
    ],
    "layers": [],
}
