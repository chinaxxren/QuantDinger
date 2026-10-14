# ============================================================
# [Default] PMax on RSI w T3
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Custom RSI, Tillson T3 support, and ATR PMax trailing levels in a
# separate pane. Signals are visual markers only; this source never trades.
# ============================================================

my_indicator_name = "[Default] PMax on RSI w T3"
my_indicator_description = (
    "Custom RSI smoothed by Tillson T3 with ATR-based PMax trailing levels "
    "and chart-only crossover signals."
)

# @param source str hl2 Price source: hl2, hlc3, close, open, high, or low
# @param multiplier float 1.0 ATR multiplier for the PMax trailing levels range=0.1:10:0.1
# @param t3_length int 8 Tillson T3 smoothing length range=2:100:1
# @param t3_factor float 0.7 Tillson T3 volume factor range=0:1:0.05
# @param atr_length int 10 RSI ATR smoothing length range=2:100:1
# @param rsi_length int 14 Custom RSI length range=2:100:1
# @param show_rsi bool True Show the RSI line
# @param show_support bool True Show the T3 support line
# @param show_signals bool True Show chart-only Buy/Sell markers
# @param highlighting bool True Show bull/bear highlight boundaries

source_name = str(params.get("source", "hl2")).lower()
multiplier = max(0.1, float(params.get("multiplier", 1.0)))
t3_length = max(2, int(params.get("t3_length", 8)))
t3_factor = min(1.0, max(0.0, float(params.get("t3_factor", 0.7))))
atr_length = max(2, int(params.get("atr_length", 10)))
rsi_length = max(2, int(params.get("rsi_length", 14)))
show_rsi = bool(params.get("show_rsi", True))
show_support = bool(params.get("show_support", True))
show_signals = bool(params.get("show_signals", True))
highlighting = bool(params.get("highlighting", True))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
open_price = df["open"].astype(float) if "open" in df else close

source_map = {
    "hl2": (high + low) / 2.0,
    "hlc3": (high + low + close) / 3.0,
    "close": close,
    "open": open_price,
    "high": high,
    "low": low,
}
price_source = source_map.get(source_name, source_map["hl2"])

# Wilder's moving average (WWMA/RMA) with a causal first-value seed.
def wwma(values, length):
    return values.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

# The original indicator blends WWMA and SMA for its custom RSI. The high/low
# ranges are also fed into the RSI envelope used to calculate the RSI ATR.
change = price_source.diff()
up = change.clip(lower=0.0)
down = (-change).clip(lower=0.0)
up_wilder = wwma(up, rsi_length)
down_wilder = wwma(down, rsi_length)
up_sma = up.rolling(rsi_length, min_periods=rsi_length).mean()
down_sma = down.rolling(rsi_length, min_periods=rsi_length).mean()

average_up = (up_wilder + up_sma) / 2.0
average_down = (down_wilder + down_sma) / 2.0
relative_strength = average_up / average_down.replace(0.0, np.nan)
rsi = (100.0 - 100.0 / (1.0 + relative_strength)).clip(0.0, 100.0)
rsi = rsi.where(average_down > 0.0, 100.0)
rsi = rsi.where(~((average_up == 0.0) & (average_down == 0.0)), 50.0)

# Build causal RSI high/low envelopes from the current bar's range versus the
# previous close. They make the PMax ATR react to an expanding RSI range.
previous_close = close.shift(1)
high_move = (high - previous_close).clip(lower=0.0)
low_move = (previous_close - low).clip(lower=0.0)
range_scale = (high - low).abs() / price_source.abs().replace(0.0, np.nan) * 100.0
range_scale = range_scale.replace([np.inf, -np.inf], np.nan)
range_scale = range_scale.fillna(0.0)

high_adjustment = wwma(high_move, rsi_length) / price_source.abs().replace(0.0, np.nan) * 100.0
low_adjustment = wwma(low_move, rsi_length) / price_source.abs().replace(0.0, np.nan) * 100.0
high_adjustment = high_adjustment.replace([np.inf, -np.inf], np.nan).fillna(0.0)
low_adjustment = low_adjustment.replace([np.inf, -np.inf], np.nan).fillna(0.0)
rsih = (rsi + high_adjustment + range_scale / 2.0).clip(0.0, 100.0)
rsil = (rsi - low_adjustment - range_scale / 2.0).clip(0.0, 100.0)

rsi_values = rsi.to_numpy(dtype=float)
rsih_values = rsih.to_numpy(dtype=float)
rsil_values = rsil.to_numpy(dtype=float)
n = len(df)

# RSI-based true range and simple moving-average ATR.
rsi_previous = np.concatenate([[np.nan], rsi_values[:-1]])
rsi_tr = np.maximum(
    rsih_values - rsil_values,
    np.maximum(np.abs(rsih_values - rsi_previous), np.abs(rsil_values - rsi_previous)),
)
rsi_tr_series = pd.Series(rsi_tr, index=df.index)
atr = rsi_tr_series.rolling(atr_length, min_periods=atr_length).mean()

# Tillson T3: six causal EMA passes and the standard volume-factor weights.
e1 = rsi.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
e2 = e1.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
e3 = e2.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
e4 = e3.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
e5 = e4.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
e6 = e5.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()
a = t3_factor
c1 = -(a ** 3)
c2 = 3.0 * (a ** 2) + 3.0 * (a ** 3)
c3 = -6.0 * (a ** 2) - 3.0 * a - 3.0 * (a ** 3)
c4 = 1.0 + 3.0 * a + (a ** 3) + 3.0 * (a ** 2)
t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3

atr_values = atr.to_numpy(dtype=float)
t3_values = t3.to_numpy(dtype=float)
long_basic = t3_values - multiplier * atr_values
short_basic = t3_values + multiplier * atr_values
long_stop = np.full(n, np.nan, dtype=float)
short_stop = np.full(n, np.nan, dtype=float)
pmax = np.full(n, np.nan, dtype=float)
direction = np.zeros(n, dtype=np.int8)

# PMax uses one-sided ratchets and flips only when T3 crosses the prior stop.
for i in range(n):
    if not np.isfinite(t3_values[i]) or not np.isfinite(long_basic[i]) or not np.isfinite(short_basic[i]):
        if i > 0:
            direction[i] = direction[i - 1]
        continue

    if i == 0 or direction[i - 1] == 0 or not np.isfinite(pmax[i - 1]):
        long_stop[i] = long_basic[i]
        short_stop[i] = short_basic[i]
        direction[i] = 1
        pmax[i] = long_stop[i]
        continue

    previous_long = long_stop[i - 1]
    previous_short = short_stop[i - 1]
    previous_t3 = t3_values[i - 1]
    if np.isfinite(previous_long) and previous_t3 > previous_long:
        long_stop[i] = max(long_basic[i], previous_long)
    else:
        long_stop[i] = long_basic[i]
    if np.isfinite(previous_short) and previous_t3 < previous_short:
        short_stop[i] = min(short_basic[i], previous_short)
    else:
        short_stop[i] = short_basic[i]

    previous_direction = direction[i - 1]
    if previous_direction == -1 and t3_values[i] > previous_short:
        direction[i] = 1
    elif previous_direction == 1 and t3_values[i] < previous_long:
        direction[i] = -1
    else:
        direction[i] = previous_direction
    pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]

previous_t3 = np.concatenate([[np.nan], t3_values[:-1]])
previous_pmax = np.concatenate([[np.nan], pmax[:-1]])
long_signal = (
    np.isfinite(t3_values)
    & np.isfinite(pmax)
    & np.isfinite(previous_t3)
    & np.isfinite(previous_pmax)
    & (t3_values > pmax)
    & (previous_t3 <= previous_pmax)
)
short_signal = (
    np.isfinite(t3_values)
    & np.isfinite(pmax)
    & np.isfinite(previous_t3)
    & np.isfinite(previous_pmax)
    & (t3_values < pmax)
    & (previous_t3 >= previous_pmax)
)

# Use the direction selected by PMax for the optional bull/bear boundaries.
rsi_up = np.where((direction > 0) & np.isfinite(rsi_values), rsi_values, np.nan)
pmax_up = np.where((direction > 0) & np.isfinite(pmax), pmax, np.nan)
rsi_dn = np.where((direction < 0) & np.isfinite(rsi_values), rsi_values, np.nan)
pmax_dn = np.where((direction < 0) & np.isfinite(pmax), pmax, np.nan)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


none_values = [None] * n
output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "RSI",
            "data": plot_list(rsi_values) if show_rsi else none_values,
            "color": "#8E1599",
            "overlay": False,
        },
        {
            "name": "T3 Support",
            "data": plot_list(t3_values) if show_support else none_values,
            "color": "#111111",
            "overlay": False,
            "width": 2,
        },
        {
            "name": "PMax",
            "data": plot_list(pmax),
            "color": "#E53935",
            "overlay": False,
            "width": 2,
        },
        {"name": "RSI Upper", "data": [70.0] * n, "color": "#9E9E9E", "overlay": False},
        {"name": "RSI Lower", "data": [30.0] * n, "color": "#9E9E9E", "overlay": False},
        {
            "name": "Bull RSI Highlight",
            "data": plot_list(rsi_up) if highlighting else none_values,
            "color": "#26A69A",
            "overlay": False,
        },
        {
            "name": "Bull PMax Highlight",
            "data": plot_list(pmax_up) if highlighting else none_values,
            "color": "#26A69A",
            "overlay": False,
        },
        {
            "name": "Bear RSI Highlight",
            "data": plot_list(rsi_dn) if highlighting else none_values,
            "color": "#EF5350",
            "overlay": False,
        },
        {
            "name": "Bear PMax Highlight",
            "data": plot_list(pmax_dn) if highlighting else none_values,
            "color": "#EF5350",
            "overlay": False,
        },
    ],
    "signals": [
        {
            "type": "buy",
            "text": "Buy",
            "data": [
                float(pmax[i] * 0.995) if show_signals and long_signal[i] and np.isfinite(pmax[i]) else None
                for i in range(n)
            ],
            "color": "#00C853",
        },
        {
            "type": "sell",
            "text": "Sell",
            "data": [
                float(pmax[i] * 1.005) if show_signals and short_signal[i] and np.isfinite(pmax[i]) else None
                for i in range(n)
            ],
            "color": "#D50000",
        },
    ],
    "metadata": {
        "causal": True,
        "source": source_name if source_name in source_map else "hl2",
        "direction": [int(value) if value else None for value in direction],
        "long_signal": [bool(value) for value in long_signal],
        "short_signal": [bool(value) for value in short_signal],
    },
    "layers": [],
}
