# ============================================================
# [Default] kNN Lorentzian Machine Learning
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal k-nearest-neighbor classifier based on Lorentzian distance.
# This is a chart-only implementation of the MiniBT/TradingView-style
# kNN Lorentzian Machine Learning engine; it never places or manages orders.
# ============================================================

my_indicator_name = "[Default] kNN Lorentzian Machine Learning"
my_indicator_description = (
    "Causal Lorentzian-distance kNN classifier with normalized RSI, WaveTrend, "
    "CCI, ADX, and momentum features."
)

# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param k_neighbors int 8 Number of nearest neighbors range=1:32:1
# @param confidence_threshold float 0.7 Minimum vote confidence range=0.5:1.0:0.05
# @param max_lookback int 2000 Maximum historical search window range=100:5000:100
# @param step_size int 1 Historical candidate stride range=1:20:1
# @param target_len int 3 Target direction horizon range=1:50:1
# @param norm_len int 150 Feature normalization window range=20:1000:10
# @param feature_count int 5 Number of features used by kNN range=1:5:1
# @param f1_string string RSI Feature 1: RSI, WT, CCI, ADX, or Mom
# @param f1_paramA int 14 Feature 1 primary length range=2:100:1
# @param f1_paramB int 1 Feature 1 secondary length range=1:50:1
# @param f2_string string WT Feature 2: RSI, WT, CCI, ADX, or Mom
# @param f2_paramA int 10 Feature 2 primary length range=2:100:1
# @param f2_paramB int 11 Feature 2 secondary length range=1:50:1
# @param f3_string string CCI Feature 3: RSI, WT, CCI, ADX, or Mom
# @param f3_paramA int 20 Feature 3 primary length range=2:100:1
# @param f3_paramB int 1 Feature 3 secondary length range=1:50:1
# @param f4_string string ADX Feature 4: RSI, WT, CCI, ADX, or Mom
# @param f4_paramA int 20 Feature 4 primary length range=2:100:1
# @param f4_paramB int 1 Feature 4 secondary length range=1:50:1
# @param f5_string string Mom Feature 5: RSI, WT, CCI, ADX, or Mom
# @param f5_paramA int 10 Feature 5 primary length range=2:100:1
# @param f5_paramB int 1 Feature 5 secondary length range=1:50:1


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
    first = np.flatnonzero(np.isfinite(result))
    if len(first) == 0:
        return result
    start = int(first[0])
    for i in range(start + 1, len(values)):
        if np.isfinite(values[i]) and np.isfinite(result[i - 1]):
            result[i] = (result[i - 1] * (length - 1.0) + values[i]) / length
        else:
            result[i] = result[i - 1]
    return result


def _true_range(high, low, close):
    result = np.full(len(close), np.nan, dtype=float)
    if len(close) == 0:
        return result
    result[0] = high[0] - low[0]
    for i in range(1, len(close)):
        result[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return result


def _rsi(close, length):
    delta = np.full(len(close), np.nan, dtype=float)
    if len(close) > 1:
        delta[1:] = np.diff(close)
    gain = np.where(np.isfinite(delta) & (delta > 0.0), delta, 0.0)
    loss = np.where(np.isfinite(delta) & (delta < 0.0), -delta, 0.0)
    avg_gain = _rma(gain, length)
    avg_loss = _rma(loss, length)
    ratio = np.divide(
        avg_gain,
        avg_loss,
        out=np.full(len(close), np.nan),
        where=np.isfinite(avg_loss) & (avg_loss > 0.0),
    )
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
        result[i] = 0.0 if deviation <= 1e-12 else (typical[i] - middle) / (0.015 * deviation)
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
    plus_di = np.divide(
        100.0 * _rma(plus_dm, length),
        smooth_tr,
        out=np.full(len(close), np.nan),
        where=np.isfinite(smooth_tr) & (smooth_tr > 0.0),
    )
    minus_di = np.divide(
        100.0 * _rma(minus_dm, length),
        smooth_tr,
        out=np.full(len(close), np.nan),
        where=np.isfinite(smooth_tr) & (smooth_tr > 0.0),
    )
    denominator = plus_di + minus_di
    dx = np.divide(
        100.0 * np.abs(plus_di - minus_di),
        denominator,
        out=np.full(len(close), np.nan),
        where=np.isfinite(denominator) & (denominator > 0.0),
    )
    return _rma(dx, length)


def _wavetrend(high, low, close, length_a, length_b):
    source = (high + low + close) / 3.0
    esa = _ema(source, length_a)
    deviation = _ema(np.abs(source - esa), length_a)
    ci = np.divide(
        source - esa,
        0.015 * deviation,
        out=np.full(len(close), np.nan),
        where=np.isfinite(deviation) & (deviation > 1e-12),
    )
    return _ema(ci, max(1, length_b))


def _raw_feature(name, pa, pb, high, low, close):
    name = str(name or "RSI").strip().upper()
    pa = max(2, int(pa))
    pb = max(1, int(pb))
    if name == "WT":
        return _wavetrend(high, low, close, pa, pb)
    if name == "CCI":
        return _cci(high, low, close, pa)
    if name == "ADX":
        return _adx(high, low, close, pa)
    if name == "MOM":
        result = np.full(len(close), np.nan, dtype=float)
        if len(close) > pa:
            result[pa:] = close[pa:] - close[:-pa]
        return result
    return _rsi(close, pa)


def _minmax_normalize(values, length):
    series = pd.Series(values)
    minimum = series.rolling(length, min_periods=length).min().to_numpy()
    maximum = series.rolling(length, min_periods=length).max().to_numpy()
    result = np.full(len(values), 50.0, dtype=float)
    valid = np.isfinite(values) & np.isfinite(minimum) & np.isfinite(maximum)
    span = maximum - minimum
    valid &= np.isfinite(span) & (span > 1e-5)
    result[valid] = (values[valid] - minimum[valid]) / span[valid] * 100.0
    return np.clip(result, 0.0, 100.0)


def _as_source(df):
    open_price = df["open"].astype(float).to_numpy()
    high = df["high"].astype(float).to_numpy()
    low = df["low"].astype(float).to_numpy()
    close = df["close"].astype(float).to_numpy()
    source_name = str(params.get("source", "close")).strip().lower()
    if source_name == "hl2":
        source = (high + low) / 2.0
    elif source_name == "hlc3":
        source = (high + low + close) / 3.0
    elif source_name == "ohlc4":
        source = (open_price + high + low + close) / 4.0
    else:
        source = close.copy()
    return source, high, low, close


# Parameter coercion is deliberately local so this source can execute in the
# restricted indicator sandbox without importing application code.
df = df.copy()
source, high, low, close = _as_source(df)
n = len(source)
k_neighbors = max(1, min(32, int(params.get("k_neighbors", 8))))
confidence_threshold = float(np.clip(float(params.get("confidence_threshold", 0.7)), 0.5, 1.0))
max_lookback = max(100, min(5000, int(params.get("max_lookback", 2000))))
step_size = max(1, min(20, int(params.get("step_size", 1))))
target_len = max(1, min(50, int(params.get("target_len", 3))))
norm_len = max(20, min(1000, int(params.get("norm_len", 150))))
feature_count = max(1, min(5, int(params.get("feature_count", 5))))

feature_specs = []
for index in range(1, 6):
    name = params.get("f%d_string" % index, ("RSI", "WT", "CCI", "ADX", "Mom")[index - 1])
    pa = params.get("f%d_paramA" % index, (14, 10, 20, 20, 10)[index - 1])
    pb = params.get("f%d_paramB" % index, (1, 11, 1, 1, 1)[index - 1])
    feature_specs.append((name, pa, pb))

features = []
for name, pa, pb in feature_specs:
    raw = _raw_feature(name, pa, pb, high, low, close)
    if str(name or "").strip().upper() != "WT":
        raw = _ema(raw, max(1, int(pb)))
    features.append(_minmax_normalize(raw, norm_len))
features = np.column_stack(features) if n else np.empty((0, 5), dtype=float)

# A label is based only on bars that are already closed.  The current bar and
# the immediately preceding bar are excluded from the candidate set, matching
# the source engine's no-look-ahead behavior.
target = np.zeros(n, dtype=np.int64)
if n > target_len:
    target[target_len:] = (source[target_len:] >= source[:-target_len]).astype(np.int64)

signal = np.zeros(n, dtype=float)
confidence = np.full(n, np.nan, dtype=float)
for t in range(n):
    start_candidate = max(target_len, t - max_lookback)
    candidates = np.arange(t - 2, start_candidate - 1, -step_size)
    if len(candidates) <= k_neighbors + 6:
        continue
    current = features[t, :feature_count]
    historical = features[candidates, :feature_count]
    valid = np.isfinite(current) & np.all(np.isfinite(historical), axis=0)
    if not np.all(valid):
        continue
    distances = np.log1p(np.abs(historical - current)).sum(axis=1)
    order = np.argsort(distances, kind="stable")[:k_neighbors]
    confidence[t] = float(np.sum(target[candidates[order]])) / float(k_neighbors)
    if confidence[t] >= confidence_threshold:
        signal[t] = 1.0
    elif confidence[t] <= 1.0 - confidence_threshold:
        signal[t] = -1.0

previous_signal = np.concatenate(([0.0], signal[:-1])) if n else np.empty(0, dtype=float)
long_signal = (signal == 1.0) & (previous_signal != 1.0)
short_signal = (signal == -1.0) & (previous_signal != -1.0)
exit_long_signal = (previous_signal == 1.0) & (signal == 0.0)
exit_short_signal = (previous_signal == -1.0) & (signal == 0.0)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


buy_marks = [float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None for i in range(n)]
exit_long_marks = [float(high[i]) * 1.002 if exit_long_signal[i] and np.isfinite(high[i]) else None for i in range(n)]
exit_short_marks = [float(low[i]) * 0.998 if exit_short_signal[i] and np.isfinite(low[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Signal", "data": plot_list(signal), "color": "#26A69A", "overlay": False},
        {"name": "Confidence", "data": plot_list(confidence), "color": "#7E57C2", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "kNN Long", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "kNN Short", "data": sell_marks, "color": "#FF5252"},
        {"type": "exit_long", "text": "kNN Exit Long", "data": exit_long_marks, "color": "#FF9800"},
        {"type": "exit_short", "text": "kNN Exit Short", "data": exit_short_marks, "color": "#26C6DA"},
    ],
    "layers": [],
}
