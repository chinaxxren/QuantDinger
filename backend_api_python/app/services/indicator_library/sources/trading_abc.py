# ============================================================
# [Default] Trading ABC
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal moving-average trend, ZigZag, and ABC retracement detector.
# Every event is emitted on the bar that confirms it; historical bars are
# never rewritten with information from a later bar.
# ============================================================

my_indicator_name = "[Default] Trading ABC"
my_indicator_description = "Causal moving-average trend, ZigZag, and ABC retracement chart indicator."

# @param prd int 8 ZigZag lookback range=2:40:1
# @param fiboup float 0.618 Upper Fibonacci retracement range=0.1:1.5:0.001
# @param fibodn float 0.382 Lower Fibonacci retracement range=0.1:1.5:0.001
# @param errorrate float 5.0 ABC ratio tolerance percent range=0.0:25.0:0.5
# @param src_ma str close Moving-average source choices=close,hl2,hlc3,ohlc4
# @param malen1 int 50 SMA length range=2:300:1
# @param malen2 int 100 SMA length range=2:300:1
# @param malen3 int 150 SMA length range=2:300:1
# @param malen4 int 200 SMA length range=2:300:1
# @param malen5 int 20 EMA length range=2:300:1
# @param malen6 int 40 EMA length range=2:300:1
# @param showabc bool true Show the ABC retracement line
# @param keepabc bool true Keep confirmed ABC lines visible
# @param showcloud bool true Use the moving-average trend filter
# @param showzigzag bool true Show the causal ZigZag points


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


prd = _clamp_int(params.get("prd", 8), 8, 2, 40)
fiboup = _clamp_float(params.get("fiboup", 0.618), 0.618, 0.1, 1.5)
fibodn = _clamp_float(params.get("fibodn", 0.382), 0.382, 0.1, 1.5)
errorrate = _clamp_float(params.get("errorrate", 5.0), 5.0, 0.0, 25.0)
src_ma = str(params.get("src_ma", "close")).strip().lower()
if src_ma not in ("close", "hl2", "hlc3", "ohlc4"):
    src_ma = "close"

malen1 = _clamp_int(params.get("malen1", 50), 50, 2, 300)
malen2 = _clamp_int(params.get("malen2", 100), 100, 2, 300)
malen3 = _clamp_int(params.get("malen3", 150), 150, 2, 300)
malen4 = _clamp_int(params.get("malen4", 200), 200, 2, 300)
malen5 = _clamp_int(params.get("malen5", 20), 20, 2, 300)
malen6 = _clamp_int(params.get("malen6", 40), 40, 2, 300)
showabc = _as_bool(params.get("showabc", True), True)
keepabc = _as_bool(params.get("keepabc", True), True)
showcloud = _as_bool(params.get("showcloud", True), True)
showzigzag = _as_bool(params.get("showzigzag", True), True)


df = df.copy()
open_values = df["open"].astype(float).to_numpy()
high_values = df["high"].astype(float).to_numpy()
low_values = df["low"].astype(float).to_numpy()
close_values = df["close"].astype(float).to_numpy()
n = len(df)

if src_ma == "hl2":
    ma_source = (df["high"].astype(float) + df["low"].astype(float)) / 2.0
elif src_ma == "hlc3":
    ma_source = (
        df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)
    ) / 3.0
elif src_ma == "ohlc4":
    ma_source = (
        df["open"].astype(float)
        + df["high"].astype(float)
        + df["low"].astype(float)
        + df["close"].astype(float)
    ) / 4.0
else:
    ma_source = df["close"].astype(float)

sma_lengths = (malen1, malen2, malen3, malen4)
ema_lengths = (malen5, malen6)
ma_series = [
    ma_source.rolling(length, min_periods=length).mean().to_numpy(dtype=float)
    for length in sma_lengths
]
ma_series.extend(
    [ma_source.ewm(span=length, adjust=False, min_periods=length).mean().to_numpy(dtype=float) for length in ema_lengths]
)

# The trend filter only changes after two consecutive qualifying bars.
trend = np.zeros(n, dtype=float)
upper_count = np.zeros(n, dtype=float)
lower_count = np.zeros(n, dtype=float)
up_streak = 0
down_streak = 0
current_trend = 0
for i in range(n):
    body_top = max(open_values[i], close_values[i])
    body_bottom = min(open_values[i], close_values[i])
    upper = 0
    lower = 0
    for ma in ma_series:
        if np.isfinite(ma[i]):
            if ma[i] > body_top:
                upper += 1
            elif ma[i] < body_bottom:
                lower += 1
    upper_count[i] = upper
    lower_count[i] = lower
    if showcloud and lower > 0 and upper == 0:
        up_streak += 1
        down_streak = 0
    elif showcloud and upper > 0 and lower == 0:
        down_streak += 1
        up_streak = 0
    else:
        up_streak = 0
        down_streak = 0
    if up_streak >= 2:
        current_trend = 1
    elif down_streak >= 2:
        current_trend = -1
    trend[i] = current_trend

# Causal ZigZag. A point is created or updated only at the current bar using
# the trailing lookback window; no future candle is used to back-fill a pivot.
zz_direction = 0
zz_points = []
zz_plot = np.full(n, np.nan, dtype=float)
zz_direction_plot = np.zeros(n, dtype=float)
abc_line = np.full(n, np.nan, dtype=float)
abc_rate_plot = np.full(n, np.nan, dtype=float)
abc_state = np.zeros(n, dtype=float)
abc_events = [None] * n
abc_point_events = [None] * n
abc_active = False
abc_start = -1
abc_is_bullish = False
abc_end_index = -1
abc_end_value = np.nan

for i in range(n):
    start = max(0, i - prd + 1)
    window_high = high_values[start : i + 1]
    window_low = low_values[start : i + 1]
    current_high = high_values[i]
    current_low = low_values[i]
    is_high = np.isfinite(current_high) and current_high >= np.nanmax(window_high)
    is_low = np.isfinite(current_low) and current_low <= np.nanmin(window_low)

    pivot_kind = None
    pivot_value = np.nan
    if is_high and not is_low:
        pivot_kind = "high"
        pivot_value = current_high
    elif is_low and not is_high:
        pivot_kind = "low"
        pivot_value = current_low
    elif is_high and is_low:
        # A one-candle range can be both extremes. Keep the existing direction
        # when possible, otherwise use the larger candle excursion.
        if zz_direction > 0:
            pivot_kind = "high"
            pivot_value = current_high
        elif zz_direction < 0:
            pivot_kind = "low"
            pivot_value = current_low
        elif np.isfinite(open_values[i]) and close_values[i] >= open_values[i]:
            pivot_kind = "high"
            pivot_value = current_high
        else:
            pivot_kind = "low"
            pivot_value = current_low

    if pivot_kind is not None:
        next_direction = 1 if pivot_kind == "high" else -1
        if not zz_points:
            zz_points.append((i, float(pivot_value), pivot_kind))
            zz_direction = next_direction
            zz_plot[i] = float(pivot_value)
            abc_point_events[i] = pivot_kind.upper()
        elif next_direction == zz_direction and zz_points[-1][2] == pivot_kind:
            last_index, last_value, last_kind = zz_points[-1]
            should_update = (
                pivot_value > last_value if pivot_kind == "high" else pivot_value < last_value
            )
            if should_update:
                zz_points[-1] = (i, float(pivot_value), last_kind)
                zz_plot[i] = float(pivot_value)
                abc_point_events[i] = pivot_kind.upper()
        else:
            zz_points.append((i, float(pivot_value), pivot_kind))
            zz_direction = next_direction
            if len(zz_points) > 5:
                zz_points = zz_points[-5:]
            zz_plot[i] = float(pivot_value)
            abc_point_events[i] = pivot_kind.upper()

    if zz_points:
        zz_direction_plot[i] = float(zz_direction)

    # Confirm an ABC retracement only after the third causal ZigZag point.
    if len(zz_points) >= 3:
        a = zz_points[-3]
        b = zz_points[-2]
        c = zz_points[-1]
        denominator = c[1] - b[1]
        if np.isfinite(denominator) and abs(denominator) > 1e-12:
            rate = (a[1] - b[1]) / denominator
            lower_rate = fibodn * (1.0 - errorrate / 100.0)
            upper_rate = fiboup * (1.0 + errorrate / 100.0)
            if lower_rate <= rate <= upper_rate:
                if (not abc_active) or abc_end_index != c[0]:
                    abc_active = True
                    abc_start = i
                    abc_is_bullish = c[2] == "low"
                    abc_end_index = c[0]
                    abc_end_value = c[1]
                    abc_events[i] = "ABC Bull" if abc_is_bullish else "ABC Bear"
                abc_rate_plot[i] = float(rate)
            elif abc_active and i > abc_start + 6:
                abc_active = False
                abc_end_index = -1
                abc_end_value = np.nan

    if abc_active:
        abc_state[i] = 1.0 if abc_is_bullish else -1.0
        if abc_end_index >= 0 and i >= abc_start:
            if keepabc or i == abc_start:
                abc_line[i] = abc_end_value
        abc_bar_count = i - abc_start
    else:
        abc_bar_count = 999999

    previous_low = low_values[i - 1] if i > 0 else np.nan
    previous_high = high_values[i - 1] if i > 0 else np.nan
    lbounced = False
    sbounced = False
    for ma in ma_series:
        if not np.isfinite(ma[i]):
            continue
        if i > 0 and np.isfinite(previous_low):
            lbounced = lbounced or (
                min(low_values[i], previous_low) <= ma[i]
                and close_values[i] > ma[i]
                and close_values[i] > open_values[i]
            )
        if i > 0 and np.isfinite(previous_high):
            sbounced = sbounced or (
                max(high_values[i], previous_high) >= ma[i]
                and close_values[i] < ma[i]
                and close_values[i] < open_values[i]
            )

    last_zz_point = zz_points[-1][1] if zz_points else np.nan
    long_signal = (
        trend[i] == 1
        and abc_bar_count <= 6
        and abc_active
        and abc_is_bullish
        and lbounced
        and np.isfinite(last_zz_point)
        and low_values[i] >= last_zz_point
    )
    short_signal = (
        trend[i] == -1
        and abc_bar_count <= 6
        and abc_active
        and not abc_is_bullish
        and sbounced
        and np.isfinite(last_zz_point)
        and high_values[i] <= last_zz_point
    )
    if long_signal:
        abc_events[i] = "Long"
    elif short_signal:
        abc_events[i] = "Short"


def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


zz_output = _plot_list(zz_plot) if showzigzag else [None] * n
abc_output = _plot_list(abc_line) if showabc else [None] * n
long_marks = [
    float(low_values[i]) * 0.995
    if abc_events[i] == "Long" and np.isfinite(low_values[i])
    else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) * 1.005
    if abc_events[i] == "Short" and np.isfinite(high_values[i])
    else None
    for i in range(n)
]
abc_event_marks = [
    float(close_values[i]) if abc_events[i] in ("ABC Bull", "ABC Bear") else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "ZigZag", "data": zz_output, "color": "#9C27B0", "overlay": True},
        {"name": "ABC Line", "data": abc_output, "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "ABC", "data": abc_event_marks, "color": "#42A5F5"},
        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},
    ],
    "metadata": {
        "trend": [int(value) for value in trend],
        "abc": [int(value) for value in abc_state],
        "abc_rate": _plot_list(abc_rate_plot),
        "zigzag_direction": [int(value) for value in zz_direction_plot],
        "zigzag_events": abc_point_events,
        "abc_events": abc_events,
        "upper_count": [int(value) for value in upper_count],
        "lower_count": [int(value) for value in lower_count],
        "causal": True,
        "chart_only": True,
        "params": {
            "prd": prd,
            "fiboup": fiboup,
            "fibodn": fibodn,
            "errorrate": errorrate,
            "src_ma": src_ma,
            "showabc": showabc,
            "keepabc": keepabc,
            "showcloud": showcloud,
            "showzigzag": showzigzag,
        },
    },
    "layers": [],
}
