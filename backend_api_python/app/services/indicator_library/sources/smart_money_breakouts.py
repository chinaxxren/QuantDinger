# ============================================================
# [Default] Smart Money Breakouts
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal swing-pivot liquidity breakout indicator inspired by
# Smart Money Breakouts [ChartPrime]. It emits chart-only BOS/CHoCH
# markers, volume-bias annotations, and optional visual TP/SL levels.
# It never places, submits, or manages real trading orders.
# ============================================================

my_indicator_name = "[Default] Smart Money Breakouts"
my_indicator_description = (
    "Causal smart-money pivot breakout detector with BOS/CHoCH signals, "
    "volume-bias labels, and optional chart-only risk levels."
)

# @param length int 20 Swing pivot left/right confirmation length range=2:100:1
# @param candle_type string Wicks Breakout source: Wicks or Body
# @param rr_ratio float 1.1 Reward/risk ratio range=0.1:20:0.1
# @param sl_type string Close Stop trigger: Close or High/Low
# @param show_sl bool False Show chart-only stop-loss line
# @param line_style string Dashed Line style: Solid, Dashed, or Dotted
# @param pivot_high_color string #028545 Pivot high color
# @param pivot_low_color string #F60707 Pivot low color
# @param tp_color string #148D9A Target color
# @param sl_color string #F60707 Stop color


def as_bool(value, default=False):
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


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


def rma(values, period):
    values = np.asarray(values, dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    if period <= 0:
        return result
    for index in range(period - 1, len(values)):
        if not np.all(np.isfinite(values[index - period + 1:index + 1])):
            continue
        if index == period - 1:
            result[index] = float(np.mean(values[:period]))
        elif np.isfinite(result[index - 1]):
            result[index] = (result[index - 1] * (period - 1) + values[index]) / period
    return result


length = clamp_int(params.get("length", 20), 20, 2, 100)
candle_type = str(params.get("candle_type", "Wicks")).strip().lower()
if candle_type not in ("wicks", "body"):
    candle_type = "wicks"
rr_ratio = clamp_float(params.get("rr_ratio", 1.1), 1.1, 0.1, 20.0)
sl_type = str(params.get("sl_type", "Close")).strip().lower()
if sl_type not in ("close", "high/low", "high_low", "highlow"):
    sl_type = "close"
show_sl = as_bool(params.get("show_sl", False), False)
line_style = str(params.get("line_style", "Dashed")).strip().lower()
if line_style not in ("solid", "dashed", "dotted"):
    line_style = "dashed"

pivot_high_color = str(params.get("pivot_high_color", "#028545"))
pivot_low_color = str(params.get("pivot_low_color", "#F60707"))
tp_color = str(params.get("tp_color", "#148D9A"))
sl_color = str(params.get("sl_color", "#F60707"))

df = df.copy()
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
open_price = (
    pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)
    if "open" in df
    else close.copy()
)
if "volume" in df:
    volume = pd.to_numeric(df["volume"], errors="coerce").to_numpy(dtype=float)
    volume = np.where(np.isfinite(volume) & (volume >= 0.0), volume, 0.0)
else:
    volume = np.ones(len(df), dtype=float)

n = len(close)
pivot_high = np.full(n, np.nan, dtype=float)
pivot_low = np.full(n, np.nan, dtype=float)
tp = np.full(n, np.nan, dtype=float)
sl = np.full(n, np.nan, dtype=float)
long_signal = np.full(n, np.nan, dtype=float)
short_signal = np.full(n, np.nan, dtype=float)
break_type = np.full(n, np.nan, dtype=float)
vol_sign = np.full(n, np.nan, dtype=float)
winning = np.zeros(n, dtype=float)
losing = np.zeros(n, dtype=float)
trade_on = np.zeros(n, dtype=float)
break_text = [None] * n
volume_text = [None] * n

true_range = np.full(n, np.nan, dtype=float)
for i in range(n):
    if not (np.isfinite(high[i]) and np.isfinite(low[i])):
        continue
    if i == 0 or not np.isfinite(close[i - 1]):
        true_range[i] = high[i] - low[i]
    else:
        true_range[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
atr = rma(true_range, 14)

active_high = np.nan
active_low = np.nan
active_high_index = None
active_low_index = None
high_active = False
low_active = False
last_break_direction = 0
position = 0
position_tp = np.nan
position_sl = np.nan
wins = 0.0
losses = 0.0

for i in range(n):
    # A pivot is only known after `length` right-side bars are complete. The
    # level is projected forward from the confirmation bar, never backfilled.
    pivot_index = i - length
    if pivot_index >= length:
        left_high = high[pivot_index - length:pivot_index]
        right_high = high[pivot_index + 1:i + 1]
        left_low = low[pivot_index - length:pivot_index]
        right_low = low[pivot_index + 1:i + 1]
        if (
            np.isfinite(high[pivot_index])
            and np.all(np.isfinite(left_high))
            and np.all(np.isfinite(right_high))
            and high[pivot_index] > np.max(left_high)
            and high[pivot_index] >= np.max(right_high)
        ):
            active_high = float(high[pivot_index])
            active_high_index = pivot_index
            high_active = True
        if (
            np.isfinite(low[pivot_index])
            and np.all(np.isfinite(left_low))
            and np.all(np.isfinite(right_low))
            and low[pivot_index] < np.min(left_low)
            and low[pivot_index] <= np.min(right_low)
        ):
            active_low = float(low[pivot_index])
            active_low_index = pivot_index
            low_active = True

    if np.isfinite(active_high):
        pivot_high[i] = active_high
    if np.isfinite(active_low):
        pivot_low[i] = active_low

    # Manage an already-open visual trade before considering a new entry. If
    # both levels are touched in one candle, stop loss wins conservatively.
    if position != 0:
        if position > 0:
            stop_hit = False
            if sl_type == "close":
                stop_hit = np.isfinite(close[i]) and close[i] <= position_sl
            else:
                stop_hit = np.isfinite(low[i]) and low[i] <= position_sl
            target_hit = np.isfinite(high[i]) and high[i] >= position_tp
            if stop_hit:
                losses += 1.0
                position = 0
            elif target_hit:
                wins += 1.0
                position = 0
        else:
            stop_hit = False
            if sl_type == "close":
                stop_hit = np.isfinite(close[i]) and close[i] >= position_sl
            else:
                stop_hit = np.isfinite(high[i]) and high[i] >= position_sl
            target_hit = np.isfinite(low[i]) and low[i] <= position_tp
            if stop_hit:
                losses += 1.0
                position = 0
            elif target_hit:
                wins += 1.0
                position = 0

    scr_high = high[i] if candle_type == "wicks" else close[i]
    scr_low = low[i] if candle_type == "wicks" else close[i]
    long_break = (
        high_active
        and np.isfinite(active_high)
        and np.isfinite(scr_high)
        and scr_high > active_high
    )
    short_break = (
        low_active
        and np.isfinite(active_low)
        and np.isfinite(scr_low)
        and scr_low < active_low
    )

    # A single candle cannot normally break both sides. Process a malformed
    # two-sided candle deterministically, with the bullish side first.
    if long_break:
        high_active = False
        if position == 0 and np.isfinite(close[i]) and np.isfinite(low[i]) and np.isfinite(atr[i]):
            distance = abs(close[i] - (low[i] - atr[i] * 1.5))
            if distance > 0.0:
                position = 1
                position_tp = close[i] + rr_ratio * distance
                position_sl = close[i] - distance
                long_signal[i] = low[i]
                break_type[i] = 1.0 if last_break_direction < 0 else 2.0
                last_break_direction = 1
                start = active_high_index + 1 if active_high_index is not None else i
                start = max(0, min(i, start))
                green_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] > open_price[start:i + 1]]))
                red_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] < open_price[start:i + 1]]))
                total_volume = green_volume + red_volume
                if total_volume > 0.0 and green_volume / total_volume > 0.55:
                    vol_sign[i] = 1.0
                    volume_text[i] = "🟢"
                elif total_volume > 0.0 and red_volume / total_volume > 0.55:
                    vol_sign[i] = 2.0
                    volume_text[i] = "🔴"
                else:
                    vol_sign[i] = 3.0
                    volume_text[i] = "🟡"
                break_text[i] = "CHoCH" if break_type[i] == 1.0 else "BOS"

    if short_break:
        low_active = False
        if position == 0 and np.isfinite(close[i]) and np.isfinite(high[i]) and np.isfinite(atr[i]):
            distance = abs(close[i] - (high[i] + atr[i] * 1.5))
            if distance > 0.0:
                position = -1
                position_tp = close[i] - rr_ratio * distance
                position_sl = close[i] + distance
                short_signal[i] = high[i]
                break_type[i] = 1.0 if last_break_direction > 0 else 2.0
                last_break_direction = -1
                start = active_low_index + 1 if active_low_index is not None else i
                start = max(0, min(i, start))
                green_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] > open_price[start:i + 1]]))
                red_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] < open_price[start:i + 1]]))
                total_volume = green_volume + red_volume
                if total_volume > 0.0 and green_volume / total_volume > 0.55:
                    vol_sign[i] = 1.0
                    volume_text[i] = "🟢"
                elif total_volume > 0.0 and red_volume / total_volume > 0.55:
                    vol_sign[i] = 2.0
                    volume_text[i] = "🔴"
                else:
                    vol_sign[i] = 3.0
                    volume_text[i] = "🟡"
                break_text[i] = "CHoCH" if break_type[i] == 1.0 else "BOS"

    if position != 0 and np.isfinite(position_tp):
        tp[i] = position_tp
        if show_sl and np.isfinite(position_sl):
            sl[i] = position_sl
    trade_on[i] = 1.0 if position != 0 else 0.0
    winning[i] = wins
    losing[i] = losses

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "Pivot High",
            "data": plot_list(pivot_high),
            "color": pivot_high_color,
            "overlay": True,
            "style": line_style,
        },
        {
            "name": "Pivot Low",
            "data": plot_list(pivot_low),
            "color": pivot_low_color,
            "overlay": True,
            "style": line_style,
        },
        {
            "name": "Take Profit",
            "data": plot_list(tp),
            "color": tp_color,
            "overlay": True,
            "style": line_style,
        },
        {
            "name": "Stop Loss",
            "data": plot_list(sl),
            "color": sl_color,
            "overlay": True,
            "style": line_style,
        },
    ],
    "signals": [
        {
            "type": "buy",
            "text": "BOS/CHoCH",
            "data": plot_list(long_signal),
            "color": "#00C853",
        },
        {
            "type": "sell",
            "text": "BOS/CHoCH",
            "data": plot_list(short_signal),
            "color": "#F23645",
        },
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "length": length,
        "candle_type": "Wicks" if candle_type == "wicks" else "Body",
        "rr_ratio": rr_ratio,
        "sl_type": "High/Low" if sl_type != "close" else "Close",
        "show_sl": show_sl,
        "line_style": line_style,
        "break_type": plot_list(break_type),
        "vol_sign": plot_list(vol_sign),
        "winning": plot_list(winning),
        "losing": plot_list(losing),
        "trade_on": plot_list(trade_on),
        "break_text": break_text,
        "volume_text": volume_text,
    },
}
