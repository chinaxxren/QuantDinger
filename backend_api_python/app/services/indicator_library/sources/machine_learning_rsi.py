# ============================================================
# [Default] Machine Learning RSI
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# K-nearest-neighbour enhanced RSI inspired by the MiniBT /
# BullVision Machine Learning RSI. This source is a chart-only
# indicator: signals are visual markers and never place orders.
# ============================================================

my_indicator_name = "[Default] Machine Learning RSI"
my_indicator_description = (
    "KNN-enhanced RSI with causal technical features and optional smoothing."
)

# @param rsi_length int 14 RSI and price-channel period range=2:100:1
# @param use_smoothing bool True Smooth the base RSI before KNN processing
# @param smoothing_length int 3 Base RSI smoothing period range=1:50:1
# @param ma_type string ALMA Base RSI moving-average type: SMA, EMA, DEMA, TEMA, WMA, VWMA, SMMA, HMA, LSMA, ALMA
# @param alma_sigma float 4 ALMA sigma range=1:10:0.5
# @param use_knn bool True Enable KNN enhancement
# @param knn_neighbors int 5 Number of nearest historical samples range=1:32:1
# @param knn_lookback int 100 Historical feature search window range=20:500:10
# @param knn_weight float 0.4 Blend weight for KNN RSI range=0:1:0.05
# @param feature_count int 3 Number of normalized features range=1:5:1
# @param use_filter bool True Apply a final RSI filter
# @param filter_method string Kalman Filter: Kalman, DoubleEMA, ALMA
# @param filter_strength float 0.3 Filter strength range=0.05:1:0.05
# @param src string close Price source: close, hl2, hlc3, or ohlc4
# @param overbought int 70 Overbought threshold range=50:95:1
# @param oversold int 30 Oversold threshold range=5:50:1
# @param color_scheme string Classic Signal color scheme
# @param neon_effect bool True Use brighter Classic colors
# @param color_mode string Trend Following RSI coloring: None, Trend Following, Impulse
# @param show_table bool True Retained for compatibility; status is returned in metadata
# @param table_position string top-left Retained for compatibility


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("false", "0", "no", "off", "none", ""):
            return False
        if normalized in ("true", "1", "yes", "on"):
            return True
    return bool(value)


def _finite(value):
    return value is not None and np.isfinite(float(value))


def _source_series(frame, name):
    close_values = frame["close"].astype(float)
    high_values = frame["high"].astype(float)
    low_values = frame["low"].astype(float)
    open_values = frame["open"].astype(float) if "open" in frame else close_values
    if name == "hl2":
        return (high_values + low_values) / 2.0
    if name == "hlc3":
        return (high_values + low_values + close_values) / 3.0
    if name == "ohlc4":
        return (open_values + high_values + low_values + close_values) / 4.0
    return close_values


def _ema(values, period):
    return values.ewm(span=period, adjust=False, min_periods=period).mean()


def _wma(values, period):
    weights = np.arange(1, period + 1, dtype=float)
    total = float(np.sum(weights))
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / total), raw=True
    )


def _vwma(values, volume, period):
    weighted = (values * volume).rolling(period, min_periods=period).sum()
    denominator = volume.rolling(period, min_periods=period).sum()
    return weighted / denominator.replace(0.0, np.nan)


def _smma(values, period):
    return values.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _linreg(values, period):
    x = np.arange(period, dtype=float)
    x_mean = float(np.mean(x))
    denominator = float(np.sum((x - x_mean) ** 2))

    def fit(window):
        y_mean = float(np.mean(window))
        slope = float(np.sum((x - x_mean) * (window - y_mean)) / denominator)
        return y_mean + slope * (period - 1 - x_mean)

    return values.rolling(period, min_periods=period).apply(fit, raw=True)


def _alma(values, period, sigma):
    if period <= 1:
        return values.copy()
    center = 0.85 * (period - 1)
    width = (period / sigma) ** 2
    weights = np.exp(-((np.arange(period, dtype=float) - center) ** 2) / (2.0 * width))
    weights = weights / float(np.sum(weights))
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights)), raw=True
    )


def _moving_average(values, period, kind, sigma, volume):
    normalized = str(kind or "ALMA").strip().upper()
    if period <= 1:
        return values.copy()
    if normalized == "SMA":
        return values.rolling(period, min_periods=period).mean()
    if normalized == "EMA":
        return _ema(values, period)
    if normalized == "DEMA":
        first = _ema(values, period)
        return 2.0 * first - _ema(first, period)
    if normalized == "TEMA":
        first = _ema(values, period)
        second = _ema(first, period)
        third = _ema(second, period)
        return 3.0 * first - 3.0 * second + third
    if normalized == "WMA":
        return _wma(values, period)
    if normalized == "VWMA":
        return _vwma(values, volume, period)
    if normalized in ("SMMA", "RMA", "WWMA"):
        return _smma(values, period)
    if normalized == "HMA":
        half = max(1, period // 2)
        root = max(1, int(np.sqrt(period)))
        return _wma(2.0 * _wma(values, half) - _wma(values, period), root)
    if normalized in ("LSMA", "LINREG", "LINEAR REGRESSION"):
        return _linreg(values, period)
    return _alma(values, period, sigma)


def _rsi(values, period):
    change = values.diff()
    gain = change.clip(lower=0.0)
    loss = (-change).clip(lower=0.0)
    average_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    total = average_gain + average_loss
    result = 100.0 * average_gain / total.replace(0.0, np.nan)
    result = result.where(average_loss > 0.0, 100.0)
    result = result.where(~((average_gain == 0.0) & (average_loss == 0.0)), 50.0)
    return result.clip(0.0, 100.0)


def _rolling_slope(values, period):
    x = np.arange(period, dtype=float)
    x_mean = float(np.mean(x))
    denominator = float(np.sum((x - x_mean) ** 2))

    def slope(window):
        y_mean = float(np.mean(window))
        return float(np.sum((x - x_mean) * (window - y_mean)) / denominator)

    return values.rolling(period, min_periods=period).apply(slope, raw=True)


def _normalize(values, period):
    lowest = values.rolling(period, min_periods=period).min()
    highest = values.rolling(period, min_periods=period).max()
    width = highest - lowest
    normalized = (values - lowest) / width.replace(0.0, np.nan)
    return normalized.where(width != 0.0, 0.5)


def _plot_values(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


rsi_length = min(100, max(2, int(params.get("rsi_length", 14))))
use_smoothing = _as_bool(params.get("use_smoothing", True), True)
smoothing_length = min(50, max(1, int(params.get("smoothing_length", 3))))
ma_type = str(params.get("ma_type", "ALMA"))
alma_sigma = min(10.0, max(1.0, float(params.get("alma_sigma", 4.0))))
use_knn = _as_bool(params.get("use_knn", True), True)
knn_neighbors = min(32, max(1, int(params.get("knn_neighbors", 5))))
knn_lookback = min(500, max(20, int(params.get("knn_lookback", 100))))
knn_weight = min(1.0, max(0.0, float(params.get("knn_weight", 0.4))))
feature_count = min(5, max(1, int(params.get("feature_count", 3))))
use_filter = _as_bool(params.get("use_filter", True), True)
filter_method = str(params.get("filter_method", "Kalman")).strip().lower()
filter_strength = min(1.0, max(0.05, float(params.get("filter_strength", 0.3))))
src_name = str(params.get("src", "close")).strip().lower()
overbought = min(100.0, max(50.0, float(params.get("overbought", 70))))
oversold = min(50.0, max(0.0, float(params.get("oversold", 30))))
color_scheme = str(params.get("color_scheme", "Classic")).strip().lower()
neon_effect = _as_bool(params.get("neon_effect", True), True)
color_mode = str(params.get("color_mode", "Trend Following")).strip().lower()
show_table = _as_bool(params.get("show_table", True), True)
table_position = str(params.get("table_position", "top-left"))

if filter_method not in ("kalman", "doubleema", "double ema", "alma"):
    filter_method = "kalman"
if color_mode not in ("none", "trend following", "impulse"):
    color_mode = "trend following"


df = df.copy()
source = _source_series(df, src_name)
volume = df["volume"].astype(float) if "volume" in df else pd.Series(1.0, index=df.index)
base_rsi = _rsi(source, rsi_length)
standard_rsi = (
    _moving_average(base_rsi, smoothing_length, ma_type, alma_sigma, volume)
    if use_smoothing
    else base_rsi
)

# Five causal features. Every normalization window contains only the current
# and prior bars; KNN candidates are always strictly earlier than the target.
features = [
    _normalize(standard_rsi, knn_lookback),
    _normalize(source.diff(3), knn_lookback),
    _normalize(source.pct_change(fill_method=None).rolling(10, min_periods=10).std(), knn_lookback),
    _normalize(_rolling_slope(source, 5), knn_lookback),
    _normalize(source.diff(5), knn_lookback),
]
feature_values = [series.to_numpy(dtype=float) for series in features]
standard_values = standard_rsi.to_numpy(dtype=float)
n = len(df)
ml_values = np.full(n, np.nan, dtype=float)
knn_values = np.full(n, np.nan, dtype=float)

for i in range(n):
    standard_value = standard_values[i]
    if not np.isfinite(standard_value):
        continue
    estimated = float(standard_value)
    if use_knn:
        current_features = [feature_values[j][i] for j in range(feature_count)]
        if all(np.isfinite(value) for value in current_features):
            start = max(0, i - knn_lookback)
            candidates = []
            for candidate in range(start, i):
                candidate_features = [feature_values[j][candidate] for j in range(feature_count)]
                candidate_rsi = standard_values[candidate]
                if not np.isfinite(candidate_rsi) or not all(np.isfinite(value) for value in candidate_features):
                    continue
                distance = float(np.sqrt(np.sum((np.asarray(current_features) - np.asarray(candidate_features)) ** 2)))
                weight = 1.0 if distance < 1e-4 else 1.0 / distance
                candidates.append((distance, candidate, float(candidate_rsi), weight))
            candidates.sort(key=lambda item: (item[0], item[1]))
            selected = candidates[:knn_neighbors]
            weight_sum = float(np.sum([item[3] for item in selected]))
            if selected and weight_sum > 0.0:
                knn_value = float(np.sum([item[2] * item[3] for item in selected]) / weight_sum)
                knn_values[i] = knn_value
                estimated = (1.0 - knn_weight) * standard_value + knn_weight * knn_value
    ml_values[i] = min(100.0, max(0.0, estimated))

# Optional causal endpoint filtering. The Kalman variant follows the source
# description directly; DoubleEMA and ALMA use equivalent one-sided smoothers.
final_values = ml_values.copy()
if use_filter:
    if filter_method == "kalman":
        previous = np.nan
        for i in range(n):
            value = ml_values[i]
            if not np.isfinite(value):
                continue
            if not np.isfinite(previous):
                previous = value
            else:
                previous = previous + filter_strength * (value - previous)
            final_values[i] = previous
    elif filter_method in ("doubleema", "double ema"):
        alpha = filter_strength
        first = np.full(n, np.nan, dtype=float)
        second = np.full(n, np.nan, dtype=float)
        for i in range(n):
            value = ml_values[i]
            if not np.isfinite(value):
                continue
            first[i] = value if i == 0 or not np.isfinite(first[i - 1]) else alpha * value + (1.0 - alpha) * first[i - 1]
            second[i] = first[i] if i == 0 or not np.isfinite(second[i - 1]) else alpha * first[i] + (1.0 - alpha) * second[i - 1]
        final_values = second
    else:
        window = max(2, int(round(2.0 + (1.0 - filter_strength) * 8.0)))
        filtered = pd.Series(ml_values, index=df.index)
        final_values = _alma(filtered, window, alma_sigma).to_numpy(dtype=float)

final_values = np.clip(final_values, 0.0, 100.0)

# Build color-segmented RSI lines. Keeping each segment in its own plot lets
# the existing frontend render the indicator without changing its layout.
rsi_bull = np.full(n, np.nan, dtype=float)
rsi_bear = np.full(n, np.nan, dtype=float)
rsi_neutral = np.full(n, np.nan, dtype=float)
rsi_gray = np.full(n, np.nan, dtype=float)
for i, value in enumerate(final_values):
    if not np.isfinite(value):
        continue
    if color_mode == "trend following":
        if value > 50.0:
            rsi_bull[i] = value
        elif value < 50.0:
            rsi_bear[i] = value
    elif color_mode == "impulse":
        if value >= overbought:
            rsi_bull[i] = value
        elif value <= oversold:
            rsi_bear[i] = value
        elif 45.0 <= value <= 55.0:
            rsi_neutral[i] = value
        else:
            rsi_gray[i] = value

previous = np.concatenate([[np.nan], final_values[:-1]])
long_signal = np.isfinite(final_values) & np.isfinite(previous) & (final_values > 50.0) & (previous <= 50.0)
short_signal = np.isfinite(final_values) & np.isfinite(previous) & (final_values < 50.0) & (previous >= 50.0)
low_values = df["low"].astype(float).to_numpy(dtype=float)
high_values = df["high"].astype(float).to_numpy(dtype=float)
long_marks = [float(low_values[i]) * 0.995 if long_signal[i] and np.isfinite(low_values[i]) else None for i in range(n)]
short_marks = [float(high_values[i]) * 1.005 if short_signal[i] and np.isfinite(high_values[i]) else None for i in range(n)]

if color_scheme == "deuteranopia":
    bull_color, bear_color = "#0072B2", "#D55E00"
elif color_scheme == "protanopia":
    bull_color, bear_color = "#009E73", "#CC79A7"
elif color_scheme == "tritanopia":
    bull_color, bear_color = "#1F77B4", "#D62728"
elif color_scheme == "monochrome":
    bull_color, bear_color = "#E0E0E0", "#757575"
elif neon_effect:
    bull_color, bear_color = "#00FF88", "#FF3D81"
else:
    bull_color, bear_color = "#00E676", "#FF5252"

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RSI Bull", "data": _plot_values(rsi_bull), "color": bull_color, "overlay": False},
        {"name": "RSI Bear", "data": _plot_values(rsi_bear), "color": bear_color, "overlay": False},
        {"name": "RSI Neutral", "data": _plot_values(rsi_neutral), "color": "#FFFFFF", "overlay": False},
        {"name": "RSI Gray", "data": _plot_values(rsi_gray), "color": "#9E9E9E", "overlay": False},
        {"name": "Midline", "data": [50.0] * n, "color": "#9E9E9E", "overlay": False, "style": "dashed"},
        {"name": "Upper", "data": [overbought] * n, "color": "#9E9E9E", "overlay": False},
        {"name": "Lower", "data": [oversold] * n, "color": "#9E9E9E", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "MLRSI+", "data": long_marks, "color": bull_color},
        {"type": "sell", "text": "MLRSI-", "data": short_marks, "color": bear_color},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "rsi": _plot_values(final_values),
        "knn_rsi": _plot_values(knn_values),
        "color_mode": color_mode,
        "color_scheme": color_scheme,
        "overbought": overbought,
        "oversold": oversold,
        "use_knn": use_knn,
        "use_filter": use_filter,
        "filter_method": filter_method,
        "show_table": show_table,
        "table_position": table_position,
    },
}
