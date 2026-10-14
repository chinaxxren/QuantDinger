# ============================================================
# [Default] HEMA Trend Levels
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Hull-style exponential moving average with causal ATR levels.  Trend state
# and markers are derived only from the current and prior bars.
# ============================================================

my_indicator_name = "[Default] HEMA Trend Levels"
my_indicator_description = "Hull-style exponential average with causal ATR trend levels and reversal markers."

# @param length int 50 HEMA period range=2:200:1
# @param atr_length int 14 ATR period range=2:200:1
# @param atr_multiplier float 1.5 ATR level multiplier range=0.1:10.0:0.1
# @param source str close Price source choices=close,hl2,hlc3,ohlc4
# @param show_levels bool True Show ATR trend levels

length = max(2, int(params.get("length", 50)))
atr_length = max(2, int(params.get("atr_length", 14)))
atr_multiplier = max(0.1, float(params.get("atr_multiplier", 1.5)))
source_name = str(params.get("source", "close")).strip().lower()
show_levels_value = params.get("show_levels", True)
show_levels = not (str(show_levels_value).strip().lower() in ("false", "0", "no", "off"))

_df = df.copy()
if source_name == "hl2":
    source = (_df["high"].astype(float) + _df["low"].astype(float)) / 2.0
elif source_name == "hlc3":
    source = (
        _df["high"].astype(float) + _df["low"].astype(float) + _df["close"].astype(float)
    ) / 3.0
elif source_name == "ohlc4":
    source = (
        _df["open"].astype(float)
        + _df["high"].astype(float)
        + _df["low"].astype(float)
        + _df["close"].astype(float)
    ) / 4.0
else:
    source_name = "close"
    source = _df["close"].astype(float)

half_length = max(1, int(length / 2))
sqrt_length = max(1, int(np.sqrt(length)))
ema_half = source.ewm(span=half_length, adjust=False, min_periods=half_length).mean()
ema_full = source.ewm(span=length, adjust=False, min_periods=length).mean()
raw_hema = 2.0 * ema_half - ema_full
hema = raw_hema.ewm(span=sqrt_length, adjust=False, min_periods=sqrt_length).mean()
hema_values = hema.to_numpy(dtype=float)

previous_close = _df["close"].astype(float).shift(1)
true_range = pd.concat(
    [
        _df["high"].astype(float) - _df["low"].astype(float),
        (_df["high"].astype(float) - previous_close).abs(),
        (_df["low"].astype(float) - previous_close).abs(),
    ],
    axis=1,
).max(axis=1)
atr_values = true_range.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean().to_numpy(dtype=float)

upper = hema_values + atr_values * atr_multiplier
lower = hema_values - atr_values * atr_multiplier
trend = np.zeros(len(_df), dtype=float)
long_signal = np.zeros(len(_df), dtype=bool)
short_signal = np.zeros(len(_df), dtype=bool)
for i in range(len(_df)):
    if not np.isfinite(hema_values[i]):
        if i > 0:
            trend[i] = trend[i - 1]
        continue
    if i > 0 and np.isfinite(hema_values[i - 1]):
        if hema_values[i] > hema_values[i - 1]:
            trend[i] = 1.0
        elif hema_values[i] < hema_values[i - 1]:
            trend[i] = -1.0
        else:
            trend[i] = trend[i - 1]
    if i > 0 and trend[i] != 0.0 and trend[i] != trend[i - 1]:
        long_signal[i] = trend[i] > 0.0
        short_signal[i] = trend[i] < 0.0


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

if not show_levels:
    upper = np.full(len(_df), np.nan, dtype=float)
    lower = np.full(len(_df), np.nan, dtype=float)

low_values = _df["low"].astype(float).to_numpy(dtype=float)
high_values = _df["high"].astype(float).to_numpy(dtype=float)
long_marks = [
    float(low_values[i]) if long_signal[i] and np.isfinite(low_values[i]) else None
    for i in range(len(_df))
]
short_marks = [
    float(high_values[i]) if short_signal[i] and np.isfinite(high_values[i]) else None
    for i in range(len(_df))
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "HEMA", "data": plot_list(hema_values), "color": "#2962FF", "overlay": True},
        {"name": "HEMA Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},
        {"name": "HEMA Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "HEMA Up", "data": long_marks, "color": "#00C853"},
        {"type": "sell", "text": "HEMA Down", "data": short_marks, "color": "#FF1744"},
    ],
    "metadata": {
        "source": source_name,
        "trend": [int(value) for value in trend],
        "atr": plot_list(atr_values),
        "show_levels": show_levels,
        "causal": True,
        "chart_only": True,
    },
    "layers": [],
}
