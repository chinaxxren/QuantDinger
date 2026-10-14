# ============================================================
# [Default] Scalping PullBack Tool
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# PAC-based pullback detector inspired by the TradingView scalping pullback
# workflow. Heikin-Ashi values are calculated recursively from the current and
# prior bars only, and pullback markers are emitted only when price crosses the
# PAC boundary on the current bar.
# ============================================================

my_indicator_name = "[Default] Scalping PullBack Tool"
my_indicator_description = (
    "PAC channel and EMA trend filter with causal pullback markers."
)

# @param hilolen int 34 PAC EMA length range=2:200:1
# @param fastlen int 89 Fast trend EMA length range=2:500:1
# @param mediumlen int 200 Medium trend EMA length range=2:1000:1
# @param slowlen int 600 Slow trend EMA length range=2:2000:1
# @param lookback int 3 Pullback lookback bars range=1:20:1
# @param delay_arrow bool false Keep signal markers on the confirmation bar
# @param use_ha bool true Use recursive Heikin-Ashi OHLC values

hilolen = max(2, int(params.get("hilolen", 34)))
fastlen = max(2, int(params.get("fastlen", 89)))
mediumlen = max(2, int(params.get("mediumlen", 200)))
slowlen = max(2, int(params.get("slowlen", 600)))
lookback = max(1, int(params.get("lookback", 3)))
delay_arrow = params.get("delay_arrow", False)
if isinstance(delay_arrow, str):
    delay_arrow = delay_arrow.strip().lower() in ("true", "1", "yes", "on")
else:
    delay_arrow = bool(delay_arrow)
use_ha = params.get("use_ha", True)
if isinstance(use_ha, str):
    use_ha = use_ha.strip().lower() in ("true", "1", "yes", "on")
else:
    use_ha = bool(use_ha)

# The source is intentionally copied so indicator execution never mutates the
# caller's market-data frame.
df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high_price = df["high"].astype(float).to_numpy()
low_price = df["low"].astype(float).to_numpy()
close_price = df["close"].astype(float).to_numpy()
n = len(df)

if use_ha:
    ha_close = (open_price + high_price + low_price + close_price) / 4.0
    ha_open = np.full(n, np.nan, dtype=float)
    if n:
        first_open = open_price[0]
        first_close = close_price[0]
        ha_open[0] = (first_open + first_close) / 2.0
        for index in range(1, n):
            previous_open = ha_open[index - 1]
            previous_close = ha_close[index - 1]
            if np.isfinite(previous_open) and np.isfinite(previous_close):
                ha_open[index] = (previous_open + previous_close) / 2.0
            else:
                ha_open[index] = (open_price[index] + close_price[index]) / 2.0
    source_high = np.maximum(high_price, np.maximum(ha_open, ha_close))
    source_low = np.minimum(low_price, np.minimum(ha_open, ha_close))
    source_close = ha_close
else:
    source_high = high_price
    source_low = low_price
    source_close = close_price

# Pandas EWM with min_periods is causal: each value only uses the current and
# earlier rows, while the initial mean avoids an artificial first-bar seed.
source_high_series = pd.Series(source_high)
source_low_series = pd.Series(source_low)
source_close_series = pd.Series(source_close)
pac_upper = source_high_series.ewm(
    span=hilolen, adjust=False, min_periods=hilolen
).mean().to_numpy()
pac_lower = source_low_series.ewm(
    span=hilolen, adjust=False, min_periods=hilolen
).mean().to_numpy()
pac_mid = source_close_series.ewm(
    span=hilolen, adjust=False, min_periods=hilolen
).mean().to_numpy()
fast_ema = source_close_series.ewm(
    span=fastlen, adjust=False, min_periods=fastlen
).mean().to_numpy()
medium_ema = source_close_series.ewm(
    span=mediumlen, adjust=False, min_periods=mediumlen
).mean().to_numpy()
slow_ema = source_close_series.ewm(
    span=slowlen, adjust=False, min_periods=slowlen
).mean().to_numpy()

buy = np.zeros(n, dtype=bool)
sell = np.zeros(n, dtype=bool)
for index in range(n):
    if index == 0:
        continue
    if not (
        np.isfinite(source_close[index])
        and np.isfinite(pac_upper[index])
        and np.isfinite(pac_lower[index])
        and np.isfinite(pac_mid[index])
        and np.isfinite(fast_ema[index])
        and np.isfinite(medium_ema[index])
        and np.isfinite(slow_ema[index])
        and np.isfinite(pac_upper[index - 1])
        and np.isfinite(pac_lower[index - 1])
    ):
        continue

    # The slow EMA confirms the broad regime; the PAC/medium relationship
    # prevents a marker when the channel is on the wrong side of the filter.
    bullish = (
        fast_ema[index] > medium_ema[index]
        and medium_ema[index] > slow_ema[index]
        and pac_lower[index] > medium_ema[index]
    )
    bearish = (
        fast_ema[index] < medium_ema[index]
        and medium_ema[index] < slow_ema[index]
        and pac_upper[index] < medium_ema[index]
    )

    window_start = max(0, index - lookback)
    prior_prices = source_close[window_start:index]
    prior_mids = pac_mid[window_start:index]
    had_long_pullback = any(
        np.isfinite(prior_prices[offset])
        and np.isfinite(prior_mids[offset])
        and prior_prices[offset] < prior_mids[offset]
        for offset in range(len(prior_prices))
    )
    had_short_pullback = any(
        np.isfinite(prior_prices[offset])
        and np.isfinite(prior_mids[offset])
        and prior_prices[offset] > prior_mids[offset]
        for offset in range(len(prior_prices))
    )

    crossed_upper = source_close[index] > pac_upper[index] and source_close[index - 1] <= pac_upper[index - 1]
    crossed_lower = source_close[index] < pac_lower[index] and source_close[index - 1] >= pac_lower[index - 1]
    buy[index] = bullish and had_long_pullback and crossed_upper
    sell[index] = bearish and had_short_pullback and crossed_lower

# ``delay_arrow`` is retained for compatibility with the original script's
# settings. It never shifts signals into the future; the marker stays on the
# bar where the pullback is confirmed.
_ = delay_arrow


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


buy_marks = [float(low_price[index]) * 0.995 if buy[index] else None for index in range(n)]
sell_marks = [float(high_price[index]) * 1.005 if sell[index] else None for index in range(n)]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "PAC Upper", "data": plot_list(pac_upper), "color": "#26A69A", "overlay": True},
        {"name": "PAC Lower", "data": plot_list(pac_lower), "color": "#EF5350", "overlay": True},
        {"name": "PAC Mid", "data": plot_list(pac_mid), "color": "#2962FF", "overlay": True},
        {"name": "Medium EMA", "data": plot_list(medium_ema), "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "PB+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "PB-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
