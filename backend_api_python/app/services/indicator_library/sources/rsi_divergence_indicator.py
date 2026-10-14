# ============================================================
# [Default] RSI Divergence Indicator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Confirmed RSI pivot divergences in a separate pane. The original MiniBT
# page includes strategy execution, but this library source intentionally
# keeps only causal chart lines and visual signals.
# ============================================================

my_indicator_name = "[Default] RSI Divergence Indicator"
my_indicator_description = (
    "Confirmed regular and hidden RSI divergences with chart-only markers."
)

# @param length int 9 RSI lookback period range=2:100:1
# @param source str close RSI source: close, hl2, hlc3, open, high, or low
# @param pivot_left int 1 Pivot left lookback range=1:20:1
# @param pivot_right int 3 Pivot right confirmation lookback range=1:20:1
# @param range_lower int 5 Minimum distance between pivots range=1:500:1
# @param range_upper int 60 Maximum distance between pivots range=2:1000:1
# @param plot_bull bool True Show regular bullish divergences
# @param plot_hidden_bull bool True Show hidden bullish divergences
# @param plot_bear bool True Show regular bearish divergences
# @param plot_hidden_bear bool False Show hidden bearish divergences

length = max(2, int(params.get("length", params.get("len", 9))))
source_name = str(params.get("source", params.get("src", "close"))).lower()
pivot_left = max(1, int(params.get("pivot_left", params.get("lbL", 1))))
pivot_right = max(1, int(params.get("pivot_right", params.get("lbR", 3))))
range_lower = max(1, int(params.get("range_lower", 5)))
range_upper = max(range_lower, int(params.get("range_upper", 60)))
plot_bull = bool(params.get("plot_bull", True))
plot_hidden_bull = bool(params.get("plot_hidden_bull", True))
plot_bear = bool(params.get("plot_bear", True))
plot_hidden_bear = bool(params.get("plot_hidden_bear", False))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
open_price = df["open"].astype(float) if "open" in df else close
source_map = {
    "close": close,
    "hl2": (high + low) / 2.0,
    "hlc3": (high + low + close) / 3.0,
    "open": open_price,
    "high": high,
    "low": low,
}
price_source = source_map.get(source_name, close)

# Use a causal Wilder RSI. The source series is selected only from the current
# and already closed bars, and the first valid value is seeded after `length`.
delta = price_source.diff()
gain = delta.clip(lower=0.0)
loss = (-delta).clip(lower=0.0)
avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)
rsi = (100.0 - 100.0 / (1.0 + relative_strength)).clip(0.0, 100.0)
rsi = rsi.where(avg_loss > 0.0, 100.0)
rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)

rsi_values = rsi.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
n = len(df)

pivot_low = np.full(n, np.nan, dtype=float)
pivot_high = np.full(n, np.nan, dtype=float)
regular_bull = np.zeros(n, dtype=bool)
hidden_bull = np.zeros(n, dtype=bool)
regular_bear = np.zeros(n, dtype=bool)
hidden_bear = np.zeros(n, dtype=bool)

# A pivot at p is emitted at p + pivot_right. This keeps all divergence
# decisions causal: the right-side confirmation bars have already closed.
for confirmation in range(pivot_left + pivot_right, n):
    pivot = confirmation - pivot_right
    current = rsi_values[pivot]
    left = rsi_values[pivot - pivot_left:pivot]
    right = rsi_values[pivot + 1:pivot + pivot_right + 1]
    if not np.isfinite(current) or len(left) != pivot_left or len(right) != pivot_right:
        continue
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        continue

    if current <= float(np.min(left)) and current < float(np.min(right)):
        pivot_low[confirmation] = current
    if current >= float(np.max(left)) and current > float(np.max(right)):
        pivot_high[confirmation] = current

# Compare each confirmed pivot with the immediately preceding pivot of the same
# type. Divergence values are placed only on the confirmation bar rather than
# backfilled across the historical segment, so appending new bars never rewrites
# already-rendered values.
previous_low_confirmation = None
previous_low_rsi = np.nan
previous_low_price = np.nan
previous_high_confirmation = None
previous_high_rsi = np.nan
previous_high_price = np.nan

for confirmation in range(n):
    current_low_rsi = pivot_low[confirmation]
    if np.isfinite(current_low_rsi):
        current_low_price = low_values[confirmation - pivot_right]
        if previous_low_confirmation is not None:
            distance = confirmation - previous_low_confirmation
            if range_lower <= distance <= range_upper and np.isfinite(current_low_price):
                regular_bull[confirmation] = (
                    current_low_price < previous_low_price and current_low_rsi > previous_low_rsi
                )
                hidden_bull[confirmation] = (
                    current_low_price > previous_low_price and current_low_rsi < previous_low_rsi
                )
        previous_low_confirmation = confirmation
        previous_low_rsi = current_low_rsi
        previous_low_price = current_low_price

    current_high_rsi = pivot_high[confirmation]
    if np.isfinite(current_high_rsi):
        current_high_price = high_values[confirmation - pivot_right]
        if previous_high_confirmation is not None:
            distance = confirmation - previous_high_confirmation
            if range_lower <= distance <= range_upper and np.isfinite(current_high_price):
                regular_bear[confirmation] = (
                    current_high_price > previous_high_price and current_high_rsi < previous_high_rsi
                )
                hidden_bear[confirmation] = (
                    current_high_price < previous_high_price and current_high_rsi > previous_high_rsi
                )
        previous_high_confirmation = confirmation
        previous_high_rsi = current_high_rsi
        previous_high_price = current_high_price


def divergence_values(enabled, condition):
    values = np.full(n, np.nan, dtype=float)
    mask = enabled & condition & np.isfinite(rsi_values)
    values[mask] = rsi_values[mask]
    return values


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


bull_values = divergence_values(plot_bull, regular_bull)
hidden_bull_values = divergence_values(plot_hidden_bull, hidden_bull)
bear_values = divergence_values(plot_bear, regular_bear)
hidden_bear_values = divergence_values(plot_hidden_bear, hidden_bear)

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RSI", "data": plot_list(rsi_values), "color": "#8D1699", "overlay": False, "width": 2},
        {"name": "RSI Upper", "data": [70.0] * n, "color": "#9E9E9E", "overlay": False},
        {"name": "RSI Lower", "data": [30.0] * n, "color": "#9E9E9E", "overlay": False},
        {"name": "RSI Middle", "data": [50.0] * n, "color": "#9E9E9E", "overlay": False},
        {"name": "Bullish Divergence", "data": plot_list(bull_values), "color": "#00C853", "overlay": False, "width": 2},
        {"name": "Hidden Bullish Divergence", "data": plot_list(hidden_bull_values), "color": "#66BB6A", "overlay": False, "width": 2},
        {"name": "Bearish Divergence", "data": plot_list(bear_values), "color": "#AB47BC", "overlay": False, "width": 2},
        {"name": "Hidden Bearish Divergence", "data": plot_list(hidden_bear_values), "color": "#EF5350", "overlay": False, "width": 2},
    ],
    "signals": [
        {
            "type": "buy",
            "text": "Bull",
            "data": plot_list(bull_values),
            "color": "#00C853",
        },
        {
            "type": "buy",
            "text": "H Bull",
            "data": plot_list(hidden_bull_values),
            "color": "#66BB6A",
        },
        {
            "type": "sell",
            "text": "Bear",
            "data": plot_list(bear_values),
            "color": "#AB47BC",
        },
        {
            "type": "sell",
            "text": "H Bear",
            "data": plot_list(hidden_bear_values),
            "color": "#EF5350",
        },
    ],
    "metadata": {
        "causal": True,
        "source": source_name if source_name in source_map else "close",
        "pivot_left": pivot_left,
        "pivot_right": pivot_right,
        "range_lower": range_lower,
        "range_upper": range_upper,
        "regular_bull": [1 if value else None for value in regular_bull],
        "hidden_bull": [1 if value else None for value in hidden_bull],
        "regular_bear": [1 if value else None for value in regular_bear],
        "hidden_bear": [1 if value else None for value in hidden_bear],
    },
    "layers": [],
}
