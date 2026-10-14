# ============================================================
# [Default] Twin Optimized Trend Tracker
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal moving-average trend tracker with twin OTT lines.  The original
# TradingView presentation offsets the twin lines by two bars; this source
# preserves that visual delay without reading future bars.
# Signals are chart markers only and never submit or manage orders.
# ============================================================

my_indicator_name = "[Default] Twin Optimized Trend Tracker"
my_indicator_description = (
    "Twin optimized trend tracker with selectable moving averages, causal "
    "trailing stops, and chart-only reversal markers."
)

# @param length int 40 Moving-average length range=1:200:1
# @param percent float 1.0 OTT percentage range=0.01:20.0:0.01
# @param coeff float 0.001 Twin-line coefficient range=0.0:0.1:0.0001
# @param ma_type string VAR Moving average: SMA, EMA, WMA, TMA, VAR, WWMA, ZLEMA, TSF
# @param var_length int 9 CMO lookback for VAR range=2:100:1
# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param ma_seed string first Recursive seed: first or zero
# @param show_support bool True Show the moving-average support line
# @param show_signals bool True Show buy/sell chart markers
# @param qty int 1 Compatibility quantity (visual only)


def as_bool(value, default):
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


def finite_or_none(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


def selected_source(frame, name):
    normalized = str(name or "close").strip().lower()
    columns = {
        "close": frame["close"].astype(float).to_numpy(copy=True),
        "hl2": ((frame["high"].astype(float) + frame["low"].astype(float)) / 2.0).to_numpy(copy=True),
        "hlc3": ((frame["high"].astype(float) + frame["low"].astype(float) + frame["close"].astype(float)) / 3.0).to_numpy(copy=True),
        "ohlc4": ((frame["open"].astype(float) + frame["high"].astype(float) + frame["low"].astype(float) + frame["close"].astype(float)) / 4.0).to_numpy(copy=True),
    }
    return columns.get(normalized, columns["close"]), normalized if normalized in columns else "close"


def rolling_sma(values, period):
    result = np.full(len(values), np.nan, dtype=float)
    running = 0.0
    count = 0
    for i, value in enumerate(values):
        if np.isfinite(value):
            running += float(value)
            count += 1
        if i >= period:
            old = values[i - period]
            if np.isfinite(old):
                running -= float(old)
                count -= 1
        if i >= period - 1 and count == period:
            result[i] = running / period
    return result


def recursive_ema(values, period, seed_mode, alpha_override=None):
    result = np.full(len(values), np.nan, dtype=float)
    alpha = float(alpha_override if alpha_override is not None else 2.0 / (period + 1.0))
    previous = 0.0
    started = False
    for i, value in enumerate(values):
        if not np.isfinite(value):
            if started:
                result[i] = previous
            continue
        if not started:
            if seed_mode == "zero":
                previous = alpha * float(value)
            else:
                previous = float(value)
            started = True
        else:
            previous = alpha * float(value) + (1.0 - alpha) * previous
        result[i] = previous
    return result


def wma(values, period):
    result = np.full(len(values), np.nan, dtype=float)
    weights = np.arange(1, period + 1, dtype=float)
    denominator = float(np.sum(weights))
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if np.all(np.isfinite(window)):
            result[i] = float(np.dot(window, weights) / denominator)
    return result


def tsf(values, period):
    result = np.full(len(values), np.nan, dtype=float)
    x = np.arange(period, dtype=float)
    x_mean = float(np.mean(x))
    denominator = float(np.sum((x - x_mean) ** 2))
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if not np.all(np.isfinite(window)) or denominator == 0.0:
            continue
        y_mean = float(np.mean(window))
        slope = float(np.sum((x - x_mean) * (window - y_mean)) / denominator)
        intercept = y_mean - slope * x_mean
        result[i] = intercept + slope * float(period - 1)
    return result


def var_average(values, period, cmo_period, seed_mode):
    delta = np.full(len(values), np.nan, dtype=float)
    if len(values) > 1:
        delta[1:] = values[1:] - values[:-1]
    up = np.where(np.isfinite(delta) & (delta > 0.0), delta, 0.0)
    down = np.where(np.isfinite(delta) & (delta < 0.0), -delta, 0.0)
    up_sum = rolling_sma(up, cmo_period) * cmo_period
    down_sum = rolling_sma(down, cmo_period) * cmo_period
    denominator = up_sum + down_sum
    cmo = np.divide(
        up_sum - down_sum,
        denominator,
        out=np.zeros(len(values), dtype=float),
        where=np.isfinite(denominator) & (denominator > 0.0),
    )
    result = np.full(len(values), np.nan, dtype=float)
    previous = 0.0
    started = False
    alpha_base = 2.0 / (period + 1.0)
    for i, value in enumerate(values):
        if not np.isfinite(value):
            if started:
                result[i] = previous
            continue
        if not started:
            previous = 0.0 if seed_mode == "zero" else float(value)
            started = True
        adaptive_alpha = float(np.clip(alpha_base * abs(cmo[i]), 0.0, 1.0))
        previous = adaptive_alpha * float(value) + (1.0 - adaptive_alpha) * previous
        result[i] = previous
    return result


length = clamp_int(params.get("length", 40), 40, 1, 200)
percent = clamp_float(params.get("percent", 1.0), 1.0, 0.01, 20.0)
coeff = clamp_float(params.get("coeff", 0.001), 0.001, 0.0, 0.1)
var_length = clamp_int(params.get("var_length", 9), 9, 2, 100)
ma_type = str(params.get("ma_type", "VAR") or "VAR").strip().upper()
if ma_type not in ("SMA", "EMA", "WMA", "TMA", "VAR", "WWMA", "ZLEMA", "TSF"):
    ma_type = "VAR"
ma_seed = str(params.get("ma_seed", "first") or "first").strip().lower()
if ma_seed not in ("first", "zero"):
    ma_seed = "first"
show_support = as_bool(params.get("show_support", True), True)
show_signals = as_bool(params.get("show_signals", True), True)
qty = clamp_int(params.get("qty", 1), 1, 1, 1000000)
prices, source_name = selected_source(df, params.get("source", "close"))
n = len(prices)

if ma_type == "SMA":
    ma_avg = rolling_sma(prices, length)
elif ma_type == "EMA":
    ma_avg = recursive_ema(prices, length, ma_seed)
elif ma_type == "WMA":
    ma_avg = wma(prices, length)
elif ma_type == "TMA":
    ma_avg = rolling_sma(rolling_sma(prices, max(1, (length + 1) // 2)), max(1, length // 2 + 1))
elif ma_type == "VAR":
    ma_avg = var_average(prices, length, var_length, ma_seed)
elif ma_type == "WWMA":
    ma_avg = recursive_ema(prices, length, ma_seed, alpha_override=1.0 / length)
elif ma_type == "ZLEMA":
    lag = max(1, (length - 1) // 2)
    adjusted = prices.copy()
    for i in range(len(adjusted)):
        if i >= lag and np.isfinite(prices[i]) and np.isfinite(prices[i - lag]):
            adjusted[i] = prices[i] + (prices[i] - prices[i - lag])
        elif not np.isfinite(prices[i]):
            adjusted[i] = np.nan
    ma_avg = recursive_ema(adjusted, length, ma_seed)
else:
    ma_avg = tsf(prices, length)

# OTT stop rails are ratcheted one bar at a time.  No future data is used.
long_stop = np.full(n, np.nan, dtype=float)
short_stop = np.full(n, np.nan, dtype=float)
direction = np.full(n, np.nan, dtype=float)
mt = np.full(n, np.nan, dtype=float)
ott = np.full(n, np.nan, dtype=float)

for i in range(n):
    if not np.isfinite(ma_avg[i]):
        if i:
            direction[i] = direction[i - 1]
        continue
    long_stop[i] = ma_avg[i] * (1.0 - percent / 100.0)
    short_stop[i] = ma_avg[i] * (1.0 + percent / 100.0)
    if i == 0 or not np.isfinite(direction[i - 1]):
        direction[i] = 1.0
    else:
        previous_long = long_stop[i - 1]
        previous_short = short_stop[i - 1]
        if np.isfinite(previous_long) and ma_avg[i] > previous_long:
            long_stop[i] = max(long_stop[i], previous_long)
        if np.isfinite(previous_short) and ma_avg[i] < previous_short:
            short_stop[i] = min(short_stop[i], previous_short)
        if direction[i - 1] < 0 and ma_avg[i] > previous_short:
            direction[i] = 1.0
        elif direction[i - 1] > 0 and ma_avg[i] < previous_long:
            direction[i] = -1.0
        else:
            direction[i] = direction[i - 1]
    mt[i] = long_stop[i] if direction[i] > 0 else short_stop[i]
    if np.isfinite(mt[i]):
        adjustment = (200.0 + percent) / 200.0 if ma_avg[i] > mt[i] else (200.0 - percent) / 200.0
        ott[i] = mt[i] * adjustment

# The two twin lines are intentionally delayed by two completed bars.  This is
# equivalent to raw[i - 2] on the current bar and remains strictly causal.
ott_up_raw = ott * (1.0 + coeff)
ott_dn_raw = ott * (1.0 - coeff)
ott_up = np.full(n, np.nan, dtype=float)
ott_dn = np.full(n, np.nan, dtype=float)
if n > 2:
    ott_up[2:] = ott_up_raw[:-2]
    ott_dn[2:] = ott_dn_raw[:-2]

previous_ma = np.concatenate(([np.nan], ma_avg[:-1]))
previous_up = np.concatenate(([np.nan], ott_up[:-1]))
previous_dn = np.concatenate(([np.nan], ott_dn[:-1]))
buy = np.isfinite(ma_avg) & np.isfinite(ott_up) & np.isfinite(previous_ma) & np.isfinite(previous_up) & (previous_ma <= previous_up) & (ma_avg > ott_up)
sell = np.isfinite(ma_avg) & np.isfinite(ott_dn) & np.isfinite(previous_ma) & np.isfinite(previous_dn) & (previous_ma >= previous_dn) & (ma_avg < ott_dn)

low = df["low"].astype(float).to_numpy(copy=True)
high = df["high"].astype(float).to_numpy(copy=True)
buy_marks = [float(low[i]) * 0.995 if show_signals and buy[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if show_signals and sell[i] and np.isfinite(high[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "MAvg", "data": finite_or_none(ma_avg) if show_support else [None] * n, "color": "#0585E1", "overlay": True},
        {"name": "OTT Upper", "data": finite_or_none(ott_up), "color": "#008000", "overlay": True},
        {"name": "OTT Lower", "data": finite_or_none(ott_dn), "color": "#FF0000", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Buy", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "Sell", "data": sell_marks, "color": "#FF0000"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "ma_type": ma_type,
        "length": length,
        "percent": percent,
        "coeff": coeff,
        "var_length": var_length,
        "source": source_name,
        "ma_seed": ma_seed,
        "show_support": show_support,
        "show_signals": show_signals,
        "qty": qty,
        "ott": finite_or_none(ott),
        "ott_up_raw": finite_or_none(ott_up_raw),
        "ott_dn_raw": finite_or_none(ott_dn_raw),
        "long_stop": finite_or_none(long_stop),
        "short_stop": finite_or_none(short_stop),
        "direction": finite_or_none(direction),
        "buy_label": buy_marks,
        "sell_label": sell_marks,
        "long_signal": [bool(value) for value in buy],
        "short_signal": [bool(value) for value in sell],
    },
}
