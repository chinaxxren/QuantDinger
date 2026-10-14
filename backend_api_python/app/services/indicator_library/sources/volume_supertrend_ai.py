# ============================================================
# [Default] Volume SuperTrend AI
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal volume-weighted SuperTrend with a nearest-neighbour trend label.
# The AI label and signals are visual context only; this indicator never
# creates, submits, or manages trading orders.
# ============================================================

my_indicator_name = "[Default] Volume SuperTrend AI"
my_indicator_description = (
    "Volume-weighted SuperTrend with causal KNN trend labels, chart-only signals, "
    "and optional cloud reference lines."
)

# @param k int 3 KNN neighbors range=1:32:1
# @param n_data int 10 KNN sample window range=1:500:1
# @param knn_price_len int 20 Price WMA period range=2:200:1
# @param knn_st_len int 100 SuperTrend WMA period range=2:500:1
# @param ai_signals bool True Show AI trend markers
# @param bullish_col string #00FF00 Bullish signal color
# @param bearish_col string #FF0000 Bearish signal color
# @param length int 10 SuperTrend baseline and ATR period range=2:200:1
# @param factor float 3.0 SuperTrend ATR multiplier range=0.1:10.0:0.1
# @param ma_src string WMA Baseline average: SMA, EMA, WMA, RMA, or VWMA
# @param up_col string #00FF00 Bullish SuperTrend color
# @param dn_col string #FF0000 Bearish SuperTrend color
# @param ne_col string #0000FF Neutral SuperTrend color
# @param show_cloud bool True Show cloud reference lines
# @param cloud_bull string #00FF00 Bullish cloud color
# @param cloud_bear string #FF0000 Bearish cloud color
# @param cloud_transp int 78 Cloud transparency range=0:100:1
# @param cloud_ref_len int 10 Cloud reference EMA period range=1:200:1
# @param cloud_line_smooth int 2 Cloud line SMA period range=1:100:1
# @param cloud_layers int 3 Cloud layers range=1:3:1


def as_bool(value, default=True):
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("false", "0", "no", "off"):
        return False
    if text in ("true", "1", "yes", "on"):
        return True
    return bool(value)


def clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if not np.isfinite(parsed):
        parsed = default
    return min(maximum, max(minimum, parsed))


def sma(values, period):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    for index in range(period - 1, len(values)):
        window = values[index - period + 1:index + 1]
        if np.all(np.isfinite(window)):
            result[index] = float(np.mean(window))
    return result


def ema(values, period):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    finite_indexes = np.where(np.isfinite(values))[0]
    if len(finite_indexes) < period:
        return result
    seed_end = int(finite_indexes[period - 1])
    seed_indexes = finite_indexes[:period]
    result[seed_end] = float(np.mean(values[seed_indexes]))
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_end + 1, len(values)):
        if np.isfinite(values[index]) and np.isfinite(result[index - 1]):
            result[index] = alpha * values[index] + (1.0 - alpha) * result[index - 1]
    return result


def rma(values, period):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    finite_indexes = np.where(np.isfinite(values))[0]
    if len(finite_indexes) < period:
        return result
    seed_end = int(finite_indexes[period - 1])
    seed_indexes = finite_indexes[:period]
    result[seed_end] = float(np.mean(values[seed_indexes]))
    alpha = 1.0 / period
    for index in range(seed_end + 1, len(values)):
        if np.isfinite(values[index]) and np.isfinite(result[index - 1]):
            result[index] = alpha * values[index] + (1.0 - alpha) * result[index - 1]
    return result


def wma(values, period):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    weights = np.arange(1.0, period + 1.0, dtype=float)
    weight_sum = float(np.sum(weights))
    for index in range(period - 1, len(values)):
        window = values[index - period + 1:index + 1]
        if np.all(np.isfinite(window)):
            result[index] = float(np.dot(window, weights) / weight_sum)
    return result


def vwma(values, volume, period):
    values = np.asarray(values, dtype=float)
    volume = np.asarray(volume, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    for index in range(period - 1, len(values)):
        value_window = values[index - period + 1:index + 1]
        volume_window = volume[index - period + 1:index + 1]
        if np.all(np.isfinite(value_window)) and np.all(np.isfinite(volume_window)):
            denominator = float(np.sum(volume_window))
            if denominator > 0.0:
                result[index] = float(np.dot(value_window, volume_window) / denominator)
    return result


def moving_average(values, period, kind, volume):
    if kind == "sma":
        return sma(values, period)
    if kind == "ema":
        return ema(values, period)
    if kind == "rma":
        return rma(values, period)
    if kind == "vwma":
        return vwma(values, volume, period)
    return wma(values, period)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


k = clamp_int(params.get("k", 3), 3, 1, 32)
n_data = clamp_int(params.get("n_data", 10), 10, 1, 500)
knn_price_len = clamp_int(params.get("knn_price_len", 20), 20, 2, 200)
knn_st_len = clamp_int(params.get("knn_st_len", 100), 100, 2, 500)
ai_signals = as_bool(params.get("ai_signals", True), True)
length = clamp_int(params.get("length", 10), 10, 2, 200)
factor = clamp_float(params.get("factor", 3.0), 3.0, 0.1, 10.0)
ma_src = str(params.get("ma_src", "WMA")).strip().lower()
if ma_src not in ("sma", "ema", "wma", "rma", "vwma"):
    ma_src = "wma"

bullish_col = str(params.get("bullish_col", "#00FF00"))
bearish_col = str(params.get("bearish_col", "#FF0000"))
up_col = str(params.get("up_col", "#00FF00"))
dn_col = str(params.get("dn_col", "#FF0000"))
ne_col = str(params.get("ne_col", "#0000FF"))
show_cloud = as_bool(params.get("show_cloud", True), True)
cloud_bull = str(params.get("cloud_bull", "#00FF00"))
cloud_bear = str(params.get("cloud_bear", "#FF0000"))
cloud_transp = clamp_int(params.get("cloud_transp", 78), 78, 0, 100)
cloud_ref_len = clamp_int(params.get("cloud_ref_len", 10), 10, 1, 200)
cloud_line_smooth = clamp_int(params.get("cloud_line_smooth", 2), 2, 1, 100)
cloud_layers = clamp_int(params.get("cloud_layers", 3), 3, 1, 3)


df = df.copy()
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
open_values = (
    pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)
    if "open" in df
    else close.copy()
)
if "volume" in df:
    volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    volume = np.maximum(volume, 0.0)
else:
    volume = np.ones(len(df), dtype=float)

n = len(close)
finite_ohlc = np.isfinite(close) & np.isfinite(high) & np.isfinite(low)
volume_input = np.where(np.isfinite(volume), volume, 0.0)
weighted_close = close * volume_input

# The baseline is volume-weighted for every supported average type, matching
# the source indicator's ma(close * volume) / ma(volume) construction.
base_numerator = moving_average(weighted_close, length, ma_src, volume_input)
base_denominator = moving_average(volume_input, length, ma_src, volume_input)
base = np.full(n, np.nan, dtype=float)
valid_base = np.isfinite(base_numerator) & np.isfinite(base_denominator) & (base_denominator > 0.0)
base[valid_base] = base_numerator[valid_base] / base_denominator[valid_base]

# Wilder ATR uses only the current and prior OHLC bars.
true_range = np.full(n, np.nan, dtype=float)
for index in range(n):
    if not finite_ohlc[index]:
        continue
    if index == 0 or not np.isfinite(close[index - 1]):
        true_range[index] = high[index] - low[index]
    else:
        true_range[index] = max(
            high[index] - low[index],
            abs(high[index] - close[index - 1]),
            abs(low[index] - close[index - 1]),
        )
atr = rma(true_range, length)

basic_lower = base - factor * atr
basic_upper = base + factor * atr
final_lower = np.full(n, np.nan, dtype=float)
final_upper = np.full(n, np.nan, dtype=float)
super_trend = np.full(n, np.nan, dtype=float)
direction = np.zeros(n, dtype=np.int8)

for index in range(n):
    if not np.isfinite(basic_lower[index]) or not np.isfinite(basic_upper[index]) or not np.isfinite(close[index]):
        continue

    if index == 0 or not np.isfinite(final_lower[index - 1]) or not np.isfinite(final_upper[index - 1]):
        final_lower[index] = basic_lower[index]
        final_upper[index] = basic_upper[index]
        direction[index] = 1
    else:
        previous_lower = final_lower[index - 1]
        previous_upper = final_upper[index - 1]
        previous_close = close[index - 1]
        final_lower[index] = (
            basic_lower[index]
            if basic_lower[index] > previous_lower or previous_close < previous_lower
            else previous_lower
        )
        final_upper[index] = (
            basic_upper[index]
            if basic_upper[index] < previous_upper or previous_close > previous_upper
            else previous_upper
        )
        if np.isclose(super_trend[index - 1], previous_upper, rtol=0.0, atol=1e-12):
            direction[index] = 1 if close[index] > final_upper[index] else -1
        else:
            direction[index] = -1 if close[index] < final_lower[index] else 1

    super_trend[index] = final_lower[index] if direction[index] > 0 else final_upper[index]

# Causal labels compare WMA(close) with WMA(superTrend). The current bar can
# receive a label, but KNN candidates are strictly earlier bars.
price_wma = wma(close, knn_price_len)
st_wma = wma(super_trend, knn_st_len)
labels = np.full(n, np.nan, dtype=float)
valid_labels = np.isfinite(price_wma) & np.isfinite(st_wma)
labels[valid_labels] = np.where(price_wma[valid_labels] > st_wma[valid_labels], 1.0, 0.0)

lookback = max(k, n_data)
ai_label = np.full(n, np.nan, dtype=float)
for index in range(n):
    if not np.isfinite(super_trend[index]):
        continue
    start = max(0, index - lookback)
    candidates = []
    for candidate in range(start, index):
        if not np.isfinite(super_trend[candidate]) or not np.isfinite(labels[candidate]):
            continue
        distance = abs(float(super_trend[index] - super_trend[candidate]))
        weight = 1.0 if distance <= 1e-12 else 1.0 / distance
        candidates.append((distance, candidate, float(labels[candidate]), weight))
    candidates.sort(key=lambda item: (item[0], item[1]))
    selected = candidates[:k]
    if selected:
        weight_sum = float(sum(item[3] for item in selected))
        if weight_sum > 0.0:
            ai_label[index] = float(sum(item[2] * item[3] for item in selected) / weight_sum)

# The original indicator treats only unanimous KNN votes as bullish/bearish;
# mixed votes remain neutral rather than being forced into a trade direction.
ai_state = np.zeros(n, dtype=np.int8)
ai_state[np.isfinite(ai_label) & (ai_label >= 1.0 - 1e-9)] = 1
ai_state[np.isfinite(ai_label) & (ai_label <= 1e-9)] = -1

st_bull = np.where((direction > 0) & (ai_state > 0), super_trend, np.nan)
st_bear = np.where((direction < 0) & (ai_state < 0), super_trend, np.nan)
st_neutral = np.where(
    np.isfinite(super_trend) & ~(((direction > 0) & (ai_state > 0)) | ((direction < 0) & (ai_state < 0))),
    super_trend,
    np.nan,
)

# Cloud reference lines remain causal. The alpha value is kept in metadata so
# clients that support fills can render the same transparency without changing
# the existing chart layout.
cloud_line = sma(super_trend, cloud_line_smooth)
cloud_ref = ema((open_values + close) / 2.0, cloud_ref_len)
cloud_a = cloud_line + (cloud_ref - cloud_line) * 0.25
cloud_b = cloud_line + (cloud_ref - cloud_line) * 0.50
cloud_c = cloud_line + (cloud_ref - cloud_line) * 0.75
if not show_cloud:
    cloud_line = np.full(n, np.nan, dtype=float)
    cloud_ref = np.full(n, np.nan, dtype=float)
    cloud_a = np.full(n, np.nan, dtype=float)
    cloud_b = np.full(n, np.nan, dtype=float)
    cloud_c = np.full(n, np.nan, dtype=float)
elif cloud_layers < 3:
    cloud_c = np.full(n, np.nan, dtype=float)
    if cloud_layers < 2:
        cloud_b = np.full(n, np.nan, dtype=float)

previous_direction = np.concatenate([[0], direction[:-1]])
previous_state = np.concatenate([[0], ai_state[:-1]])
long_event = (
    ai_signals
    & (direction > 0)
    & (previous_direction < 0)
    & (ai_state > 0)
)
short_event = (
    ai_signals
    & (direction < 0)
    & (previous_direction > 0)
    & (ai_state < 0)
)
ai_up_event = ai_signals & (ai_state > 0) & (previous_state <= 0)
ai_down_event = ai_signals & (ai_state < 0) & (previous_state >= 0)

low_values = low
high_values = high
long_marks = [
    float(low_values[index]) * 0.995
    if long_event[index] and np.isfinite(low_values[index])
    else None
    for index in range(n)
]
short_marks = [
    float(high_values[index]) * 1.005
    if short_event[index] and np.isfinite(high_values[index])
    else None
    for index in range(n)
]
ai_up_marks = [
    float(low_values[index]) * 0.99
    if ai_up_event[index] and np.isfinite(low_values[index])
    else None
    for index in range(n)
]
ai_down_marks = [
    float(high_values[index]) * 1.01
    if ai_down_event[index] and np.isfinite(high_values[index])
    else None
    for index in range(n)
]

cloud_alpha = int(round((100.0 - cloud_transp) / 100.0 * 255.0))
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Volume SuperTrend Bull", "data": plot_list(st_bull), "color": up_col, "overlay": True},
        {"name": "Volume SuperTrend Bear", "data": plot_list(st_bear), "color": dn_col, "overlay": True},
        {"name": "Volume SuperTrend Neutral", "data": plot_list(st_neutral), "color": ne_col, "overlay": True},
        {"name": "Cloud Line", "data": plot_list(cloud_line), "color": cloud_bull, "overlay": True},
        {"name": "Cloud 25%", "data": plot_list(cloud_a), "color": cloud_bull, "overlay": True},
        {"name": "Cloud 50%", "data": plot_list(cloud_b), "color": cloud_bull, "overlay": True},
        {"name": "Cloud 75%", "data": plot_list(cloud_c), "color": cloud_bear, "overlay": True},
        {"name": "Cloud Reference", "data": plot_list(cloud_ref), "color": cloud_bear, "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "AI Trend Up", "data": long_marks, "color": bullish_col},
        {"type": "sell", "text": "AI Trend Down", "data": short_marks, "color": bearish_col},
        {"type": "buy", "text": "AI Start Up", "data": ai_up_marks, "color": bullish_col, "style": "circle"},
        {"type": "sell", "text": "AI Start Down", "data": ai_down_marks, "color": bearish_col, "style": "circle"},
    ],
    "metadata": {
        "causal": True,
        "k": k,
        "n_data": n_data,
        "lookback": lookback,
        "knn_price_len": knn_price_len,
        "knn_st_len": knn_st_len,
        "length": length,
        "factor": factor,
        "ma_src": ma_src,
        "ai_signals": ai_signals,
        "show_cloud": show_cloud,
        "cloud_transp": cloud_transp,
        "cloud_alpha": cloud_alpha,
        "cloud_layers": cloud_layers,
        "super_trend": plot_list(super_trend),
        "ai_label": plot_list(ai_label),
        "direction": [int(value) if value else None for value in direction],
        "ai_state": [int(value) if value else None for value in ai_state],
        "cloud_line": plot_list(cloud_line),
        "cloud_ref": plot_list(cloud_ref),
    },
    "layers": [],
}
