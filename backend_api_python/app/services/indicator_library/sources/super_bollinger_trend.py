# ============================================================
# [Default] SuperBollingerTrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal Bollinger-band trend filter with separated trend lines,
# breakout/reversal markers, optional zigzag-style turning points, and an
# optional take-profit reference. It is chart-only and never submits orders.
# ============================================================

my_indicator_name = "[Default] SuperBollingerTrend"
my_indicator_description = (
    "Causal Bollinger trend bands with zigzag-style turning points and "
    "optional take-profit reference."
)

# @param prd int 12 Bollinger lookback range=2:200:1
# @param mult float 2.0 Bollinger deviation multiplier range=0.1:10.0:0.1
# @param show_zigzag bool True Show causal turning-point line
# @param signal str Signal Signal mode: Signal or ZigZag
# @param dev str ZigZag Signal deviation mode: ZigZag or Bollinger
# @param show_tp bool False Show take-profit reference
# @param tp_type str Median Take-profit type: Median or Basis
# @param show_table bool False Retained for source compatibility

prd = max(2, int(params.get("prd", 12)))
mult = max(0.05, float(params.get("mult", 2.0)))
show_zigzag = bool(params.get("show_zigzag", True))
signal_mode = str(params.get("signal", "Signal")).strip().lower()
dev_mode = str(params.get("dev", "ZigZag")).strip().lower()
show_tp = bool(params.get("show_tp", False))
tp_type = str(params.get("tp_type", "Median")).strip().lower()

close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)

basis_series = close.rolling(prd, min_periods=prd).mean()
std_series = close.rolling(prd, min_periods=prd).std(ddof=0)
upper_series = basis_series + mult * std_series
lower_series = basis_series - mult * std_series

basis = basis_series.to_numpy(dtype=float)
upper = upper_series.to_numpy(dtype=float)
lower = lower_series.to_numpy(dtype=float)
close_values = close.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
n = len(df)

trend = np.zeros(n, dtype=np.int8)
sbt = np.full(n, np.nan, dtype=float)
for i in range(n):
    if not np.isfinite(close_values[i]) or not np.isfinite(upper[i]) or not np.isfinite(lower[i]):
        if i > 0:
            trend[i] = trend[i - 1]
            sbt[i] = sbt[i - 1]
        continue

    previous_trend = trend[i - 1] if i else 0
    if close_values[i] > upper[i]:
        trend[i] = 1
    elif close_values[i] < lower[i]:
        trend[i] = -1
    else:
        trend[i] = previous_trend

    if trend[i] > 0:
        sbt[i] = lower[i]
    elif trend[i] < 0:
        sbt[i] = upper[i]
    else:
        sbt[i] = basis[i]

# Keep each colored line continuous across a confirmed reversal bar.
sbt_up = np.where(trend > 0, sbt, np.nan)
sbt_down = np.where(trend < 0, sbt, np.nan)
for i in range(1, n):
    if trend[i] > 0 and trend[i - 1] < 0:
        sbt_up[i - 1] = sbt[i - 1]
        sbt_up[i] = sbt[i]
    elif trend[i] < 0 and trend[i - 1] > 0:
        sbt_down[i - 1] = sbt[i - 1]
        sbt_down[i] = sbt[i]

previous_trend = np.concatenate([[0], trend[:-1]])
trend_buy = (trend == 1) & (previous_trend == -1)
trend_sell = (trend == -1) & (previous_trend == 1)

# A causal zigzag approximation: retain the latest close at a trend flip.
# No right-side pivot confirmation is used, so future bars cannot alter history.
zigzag = np.full(n, np.nan, dtype=float)
last_turn = np.nan
for i in range(n):
    if trend[i] != 0 and trend[i] != previous_trend[i]:
        last_turn = close_values[i]
    if np.isfinite(last_turn):
        zigzag[i] = last_turn

zigzag_diff = np.full(n, np.nan, dtype=float)
for i in range(1, n):
    if np.isfinite(zigzag[i]) and np.isfinite(zigzag[i - 1]):
        zigzag_diff[i] = zigzag[i] - zigzag[i - 1]
zigzag_delta = np.abs(zigzag_diff)

if signal_mode == "zigzag":
    buy = trend_buy & (zigzag_diff > 0)
    sell = trend_sell & (zigzag_diff < 0)
elif dev_mode == "bollinger":
    buy = (close_values > upper) & (previous_trend <= 0)
    sell = (close_values < lower) & (previous_trend >= 0)
else:
    buy = trend_buy
    sell = trend_sell

if tp_type == "basis":
    take_profit = basis.copy()
else:
    take_profit = ((upper + lower) / 2.0).astype(float)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

plots = [
    {"name": "SBT Up", "data": plot_list(sbt_up), "color": "#00BCD4", "overlay": True},
    {"name": "SBT Down", "data": plot_list(sbt_down), "color": "#FF5252", "overlay": True},
]
if show_zigzag:
    plots.append({"name": "ZigZag", "data": plot_list(zigzag), "color": "#9E9E9E", "overlay": True})
if show_tp:
    plots.append({"name": "Take Profit", "data": plot_list(take_profit), "color": "#FF9800", "overlay": True})

output = {
    "name": my_indicator_name,
    "plots": plots,
    "signals": [
        {
            "type": "buy",
            "text": "Buy",
            "data": [
                float(low_values[i]) * 0.995
                if buy[i] and np.isfinite(low_values[i])
                else None
                for i in range(n)
            ],
            "color": "#00C853",
        },
        {
            "type": "sell",
            "text": "Sell",
            "data": [
                float(high_values[i]) * 1.005
                if sell[i] and np.isfinite(high_values[i])
                else None
                for i in range(n)
            ],
            "color": "#FF5252",
        },
    ],
    "metadata": {
        "basis": plot_list(basis),
        "upper": plot_list(upper),
        "lower": plot_list(lower),
        "sbt": plot_list(sbt),
        "zigzag_diff": plot_list(zigzag_diff),
        "zigzag_delta": plot_list(zigzag_delta),
        "trend": [int(value) if value else None for value in trend],
        "causal": True,
    },
    "layers": [],
}
