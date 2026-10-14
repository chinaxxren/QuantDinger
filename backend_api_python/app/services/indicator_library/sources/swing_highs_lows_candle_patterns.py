# ============================================================
# [Default] Swing Highs/Lows & Candle Patterns
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Swing pivots are confirmed only after the configured right-hand bars have
# closed. Markers are emitted on the confirmation bar, not back-filled onto the
# historical pivot bar, so the series remains causal and non-repainting.
# ============================================================

my_indicator_name = "[Default] Swing Highs/Lows & Candle Patterns"
my_indicator_description = "Causal swing structure and candle-pattern detector with confirmed pivot markers."

# @param length int 21 Swing pivot left/right confirmation bars range=1:100:1

length = max(1, min(100, int(params.get("length", 21))))

df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
n = len(df)

swing_high_plot = np.full(n, np.nan, dtype=float)
swing_low_plot = np.full(n, np.nan, dtype=float)
swing_high_marker = [None] * n
swing_low_marker = [None] * n
pattern_buy_marker = [None] * n
pattern_sell_marker = [None] * n
swing_type = [None] * n
pattern_code = [None] * n
pattern_name = [None] * n

last_high_value = np.nan
last_low_value = np.nan

for i in range(n):
    # The candidate at i - length has exactly `length` bars on each side at
    # this point. Both comparisons are strict, matching the TradingView logic.
    pivot_index = i - length
    confirmed_high = False
    confirmed_low = False
    pivot_high_value = np.nan
    pivot_low_value = np.nan

    if pivot_index >= length:
        left_high = high[pivot_index - length:pivot_index]
        right_high = high[pivot_index + 1:i + 1]
        left_low = low[pivot_index - length:pivot_index]
        right_low = low[pivot_index + 1:i + 1]
        candidate_high = high[pivot_index]
        candidate_low = low[pivot_index]

        if (
            np.isfinite(candidate_high)
            and len(left_high) == length
            and len(right_high) == length
            and np.isfinite(left_high).all()
            and np.isfinite(right_high).all()
            and candidate_high > np.max(left_high)
            and candidate_high > np.max(right_high)
        ):
            confirmed_high = True
            pivot_high_value = float(candidate_high)

        if (
            np.isfinite(candidate_low)
            and len(left_low) == length
            and len(right_low) == length
            and np.isfinite(left_low).all()
            and np.isfinite(right_low).all()
            and candidate_low < np.min(left_low)
            and candidate_low < np.min(right_low)
        ):
            confirmed_low = True
            pivot_low_value = float(candidate_low)

    if confirmed_high:
        # The sparse plot carries the confirmed pivot value, while the signal
        # marker is positioned on the actual confirmation candle.
        swing_high_plot[i] = pivot_high_value
        swing_high_marker[i] = float(high[i]) * 1.005 if np.isfinite(high[i]) else None
        swing_type[i] = "HH" if not np.isfinite(last_high_value) or pivot_high_value > last_high_value else "LH"
        last_high_value = pivot_high_value

    if confirmed_low:
        swing_low_plot[i] = pivot_low_value
        swing_low_marker[i] = float(low[i]) * 0.995 if np.isfinite(low[i]) else None
        swing_type[i] = "LL" if not np.isfinite(last_low_value) or pivot_low_value < last_low_value else "HL"
        last_low_value = pivot_low_value

    # Candle patterns are evaluated on the confirmation candle using only the
    # current and immediately preceding bars.
    if i == 0:
        continue
    values = (open_price[i], high[i], low[i], close[i], open_price[i - 1], close[i - 1])
    if not all(np.isfinite(value) for value in values):
        continue

    current_open = float(open_price[i])
    current_high = float(high[i])
    current_low = float(low[i])
    current_close = float(close[i])
    previous_open = float(open_price[i - 1])
    previous_close = float(close[i - 1])
    body_size = abs(current_close - current_open)
    body_min = min(current_open, current_close)
    body_max = max(current_open, current_close)

    detected_code = None
    detected_name = None
    bullish = False

    if confirmed_low and (body_min - current_low) > body_size and (current_high - body_max) < body_size:
        detected_code = "HAM"
        detected_name = "Hammer"
        bullish = True
    elif confirmed_low and (current_high - body_max) > body_size and (body_min - current_low) < body_size:
        detected_code = "IHM"
        detected_name = "Inverted Hammer"
        bullish = True
    elif (
        current_close > current_open
        and previous_close < previous_open
        and current_close > previous_open
        and current_open < previous_close
    ):
        detected_code = "BUE"
        detected_name = "Bullish Engulfing"
        bullish = True
    elif confirmed_high and (body_min - current_low) > body_size and (current_high - body_max) < body_size:
        detected_code = "HGM"
        detected_name = "Hanging Man"
    elif confirmed_high and (current_high - body_max) > body_size and (body_min - current_low) < body_size:
        detected_code = "SS"
        detected_name = "Shooting Star"
    elif (
        current_close < current_open
        and previous_close > previous_open
        and current_close < previous_open
        and current_open > previous_close
    ):
        detected_code = "BEE"
        detected_name = "Bearish Engulfing"

    if detected_code is not None:
        pattern_code[i] = detected_code
        pattern_name[i] = detected_name
        if bullish:
            pattern_buy_marker[i] = float(current_low) * 0.99
        else:
            pattern_sell_marker[i] = float(current_high) * 1.01


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "Swing High",
            "data": plot_list(swing_high_plot),
            "color": "#FF5252",
            "overlay": True,
        },
        {
            "name": "Swing Low",
            "data": plot_list(swing_low_plot),
            "color": "#00E676",
            "overlay": True,
        },
    ],
    "signals": [
        {"type": "sell", "text": "Swing High", "data": swing_high_marker, "color": "#FF5252"},
        {"type": "buy", "text": "Swing Low", "data": swing_low_marker, "color": "#00E676"},
        {"type": "buy", "text": "Candle Buy", "data": pattern_buy_marker, "color": "#26A69A"},
        {"type": "sell", "text": "Candle Sell", "data": pattern_sell_marker, "color": "#EF5350"},
    ],
    "metadata": {
        "swing_type": swing_type,
        "pattern_code": pattern_code,
        "pattern_name": pattern_name,
    },
    "layers": [],
}
