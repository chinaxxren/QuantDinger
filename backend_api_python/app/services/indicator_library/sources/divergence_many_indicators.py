# ============================================================
# [Default] Divergence for Many Indicators v4
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal regular/hidden divergence detector inspired by the TradingView
# "Divergence for Many Indicators v4" study. Pivot points are only emitted
# after their right-hand confirmation window closes, so no future bar is used
# at the time a signal is displayed. This source only produces chart output.
# ============================================================

my_indicator_name = "[Default] Divergence for Many Indicators v4"
my_indicator_description = (
    "Causal regular and hidden bullish/bearish divergence detection across "
    "multiple momentum and volume indicators."
)

# @param pivot_period int 5 Pivot confirmation width range=2:20:1
# @param source string Close Price pivot source: Close or High/Low
# @param div_type string Regular Divergence type: Regular, Hidden, or Both
# @param max_bars int 100 Maximum pivot distance range=10:500:10
# @param show_names string Full Signal label detail: Full, Short, or None
# @param show_number bool true Append the number of confirming indicators
# @param calc_macd bool true Calculate MACD divergence
# @param calc_hist bool true Calculate MACD histogram divergence
# @param calc_rsi bool true Calculate RSI divergence
# @param calc_stoch bool true Calculate stochastic divergence
# @param calc_cci bool true Calculate CCI divergence
# @param calc_mom bool true Calculate momentum divergence
# @param calc_obv bool true Calculate OBV divergence
# @param calc_vwmacd bool true Calculate volume-weighted MACD divergence
# @param calc_cmf bool true Calculate Chaikin money-flow divergence
# @param calc_mfi bool true Calculate MFI divergence
# @param calc_ext bool false Calculate the local external momentum proxy


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


def _rolling_mean(values, length):
    return pd.Series(values).rolling(length, min_periods=length).mean().to_numpy()


def _rolling_sum(values, length):
    return pd.Series(values).rolling(length, min_periods=length).sum().to_numpy()


def _rsi(close, length=14):
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


def _cci(high, low, close, length=20):
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


def _stochastic(high, low, close, length=14):
    lowest = pd.Series(low).rolling(length, min_periods=length).min().to_numpy()
    highest = pd.Series(high).rolling(length, min_periods=length).max().to_numpy()
    return np.divide(
        100.0 * (close - lowest),
        highest - lowest,
        out=np.full(len(close), 50.0),
        where=np.isfinite(lowest) & np.isfinite(highest) & ((highest - lowest) > 1e-12),
    )


def _obv(close, volume):
    result = np.zeros(len(close), dtype=float)
    if len(close) == 0:
        return result
    for i in range(1, len(close)):
        if np.isfinite(close[i]) and np.isfinite(close[i - 1]) and np.isfinite(volume[i]):
            if close[i] > close[i - 1]:
                result[i] = result[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                result[i] = result[i - 1] - volume[i]
            else:
                result[i] = result[i - 1]
        else:
            result[i] = result[i - 1]
    return result


def _cmf(high, low, close, volume, length=20):
    spread = high - low
    multiplier = np.divide(
        (close - low) - (high - close),
        spread,
        out=np.zeros(len(close)),
        where=np.isfinite(spread) & (spread > 1e-12),
    )
    volume = np.nan_to_num(volume, nan=0.0)
    return np.divide(
        _rolling_sum(multiplier * volume, length),
        _rolling_sum(volume, length),
        out=np.full(len(close), np.nan),
        where=_rolling_sum(volume, length) > 1e-12,
    )


def _mfi(high, low, close, volume, length=14):
    typical = (high + low + close) / 3.0
    change = np.full(len(close), np.nan, dtype=float)
    if len(close) > 1:
        change[1:] = np.diff(typical)
    flow = typical * np.nan_to_num(volume, nan=0.0)
    positive = np.where(np.isfinite(change) & (change > 0.0), flow, 0.0)
    negative = np.where(np.isfinite(change) & (change < 0.0), flow, 0.0)
    upper = _rolling_sum(positive, length)
    lower = _rolling_sum(negative, length)
    ratio = np.divide(
        upper,
        lower,
        out=np.full(len(close), np.nan),
        where=np.isfinite(lower) & (lower > 1e-12),
    )
    result = 100.0 - 100.0 / (1.0 + ratio)
    result[(lower == 0.0) & (upper > 0.0)] = 100.0
    result[(lower == 0.0) & (upper == 0.0)] = 50.0
    return result


def _bool_param(name, default):
    value = params.get(name, default)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return bool(value)


def _source_pivots(source_name, high, low, close):
    source_name = str(source_name or "Close").strip().lower()
    if source_name in ("high/low", "highlow", "high_low", "high-low"):
        return low.copy(), high.copy()
    return close.copy(), close.copy()


def _pivot_points(values, period, want_high):
    indexes = []
    pivot_values = []
    for i in range(period, len(values) - period):
        current = values[i]
        left = values[i - period:i]
        right = values[i + 1:i + period + 1]
        if not np.isfinite(current) or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
            continue
        if want_high:
            valid = current >= float(np.max(left)) and current > float(np.max(right))
        else:
            valid = current <= float(np.min(left)) and current < float(np.min(right))
        if valid:
            indexes.append(i)
            pivot_values.append(float(current))
    return indexes, pivot_values


def _enabled_indicators(high, low, close, volume):
    macd = _ema(close, 12) - _ema(close, 26)
    hist = macd - _ema(macd, 9)
    momentum = np.full(len(close), np.nan, dtype=float)
    if len(close) > 10:
        momentum[10:] = close[10:] - close[:-10]
    volume_ema_fast = _ema(np.nan_to_num(close * volume, nan=0.0), 12)
    volume_ema_slow = _ema(np.nan_to_num(close * volume, nan=0.0), 26)
    volume_fast = _ema(np.nan_to_num(volume, nan=0.0), 12)
    volume_slow = _ema(np.nan_to_num(volume, nan=0.0), 26)
    vwmacd = np.divide(volume_ema_fast, volume_fast, out=np.full(len(close), np.nan), where=volume_fast > 1e-12)
    vwmacd -= np.divide(volume_ema_slow, volume_slow, out=np.zeros(len(close)), where=volume_slow > 1e-12)

    all_values = {
        "MACD": macd,
        "HIST": hist,
        "RSI": _rsi(close, 14),
        "STOCH": _stochastic(high, low, close, 14),
        "CCI": _cci(high, low, close, 20),
        "MOM": momentum,
        "OBV": _obv(close, volume),
        "VWMACD": vwmacd,
        "CMF": _cmf(high, low, close, volume, 20),
        "MFI": _mfi(high, low, close, volume, 14),
    }
    if _bool_param("calc_ext", False):
        # QuantDinger does not expose TradingView's external-security input.
        # Use a deterministic local momentum proxy when this optional line is enabled.
        all_values["EXT"] = close - _ema(close, 20)
    enabled = (
        ("MACD", "calc_macd"),
        ("HIST", "calc_hist"),
        ("RSI", "calc_rsi"),
        ("STOCH", "calc_stoch"),
        ("CCI", "calc_cci"),
        ("MOM", "calc_mom"),
        ("OBV", "calc_obv"),
        ("VWMACD", "calc_vwmacd"),
        ("CMF", "calc_cmf"),
        ("MFI", "calc_mfi"),
    )
    return [(name, all_values[name]) for name, flag in enabled if _bool_param(flag, True)] + (
        [("EXT", all_values["EXT"])] if "EXT" in all_values else []
    )


def _divergence_allowed(kind, div_type):
    div_type = str(div_type or "Regular").strip().lower()
    if div_type == "both":
        return True
    return kind == "regular" if div_type != "hidden" else kind == "hidden"


# Parameters and input arrays.
pivot_period = max(2, min(20, int(params.get("pivot_period", 5))))
max_bars = max(10, min(500, int(params.get("max_bars", 100))))
div_type = str(params.get("div_type", "Regular"))
df = df.copy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
volume = df["volume"].astype(float).to_numpy() if "volume" in df else np.ones(len(close), dtype=float)
n = len(close)
lo_source, hi_source = _source_pivots(params.get("source", "Close"), high, low, close)
lo_indexes, lo_values = _pivot_points(lo_source, pivot_period, False)
hi_indexes, hi_values = _pivot_points(hi_source, pivot_period, True)

long_code = np.zeros(n, dtype=np.int64)
short_code = np.zeros(n, dtype=np.int64)
indicators = _enabled_indicators(high, low, close, volume)

for bit, (_name, values) in enumerate(indicators):
    mask = 1 << bit
    for k in range(1, len(lo_indexes)):
        previous_index = lo_indexes[k - 1]
        current_index = lo_indexes[k]
        if current_index - previous_index > max_bars:
            continue
        previous_value = values[previous_index]
        current_value = values[current_index]
        confirmation = current_index + pivot_period
        if confirmation >= n or not np.isfinite(previous_value) or not np.isfinite(current_value):
            continue
        previous_price = lo_values[k - 1]
        current_price = lo_values[k]
        if _divergence_allowed("regular", div_type) and current_price < previous_price and current_value > previous_value:
            long_code[confirmation] |= mask
        if _divergence_allowed("hidden", div_type) and current_price > previous_price and current_value < previous_value:
            long_code[confirmation] |= mask

    for k in range(1, len(hi_indexes)):
        previous_index = hi_indexes[k - 1]
        current_index = hi_indexes[k]
        if current_index - previous_index > max_bars:
            continue
        previous_value = values[previous_index]
        current_value = values[current_index]
        confirmation = current_index + pivot_period
        if confirmation >= n or not np.isfinite(previous_value) or not np.isfinite(current_value):
            continue
        previous_price = hi_values[k - 1]
        current_price = hi_values[k]
        if _divergence_allowed("regular", div_type) and current_price > previous_price and current_value < previous_value:
            short_code[confirmation] |= mask
        if _divergence_allowed("hidden", div_type) and current_price < previous_price and current_value > previous_value:
            short_code[confirmation] |= mask

long_signal = (long_code > 0).astype(float)
short_signal = (short_code > 0).astype(float)
long_count = np.zeros(n, dtype=float)
short_count = np.zeros(n, dtype=float)
for i in range(n):
    long_count[i] = float(int(long_code[i]).bit_count())
    short_count[i] = float(int(short_code[i]).bit_count())


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


buy_marks = [float(low[i]) * 0.995 if long_signal[i] > 0.0 and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if short_signal[i] > 0.0 and np.isfinite(high[i]) else None for i in range(n)]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Long Signal", "data": plot_list(long_signal), "color": "#00E676", "overlay": False},
        {"name": "Short Signal", "data": plot_list(short_signal), "color": "#FF5252", "overlay": False},
        {"name": "Long Code", "data": plot_list(long_code), "color": "#26A69A", "overlay": False},
        {"name": "Short Code", "data": plot_list(short_code), "color": "#EF5350", "overlay": False},
        {"name": "Long Count", "data": plot_list(long_count), "color": "#66BB6A", "overlay": False},
        {"name": "Short Count", "data": plot_list(short_count), "color": "#FF7043", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "Bullish Divergence", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "Bearish Divergence", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
