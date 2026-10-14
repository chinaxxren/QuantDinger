# ============================================================
# [Default] Optimized Trend Tracker
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal VAR/CMO adaptive moving average with the OTT trailing trend line.
# This is a chart-only implementation: signals are visual markers and never
# submit, manage, or simulate orders.
# ============================================================

my_indicator_name = "[Default] Optimized Trend Tracker"
my_indicator_description = "CMO-adaptive moving average with optimized trailing trend lines."

# @param length int 2 VAR smoothing length range=1:100:1
# @param var_length int 9 CMO lookback range=2:100:1
# @param percent float 1.4 Trailing stop percentage range=0.1:10.0:0.1
# @param base int 200 OTT adjustment base range=10:1000:10

length = max(1, int(params.get("length", 2)))
var_length = max(2, int(params.get("var_length", 9)))
percent = max(0.01, float(params.get("percent", 1.4)))
base = max(2.0, float(params.get("base", 200.0)))

df = df.copy()
close = df["close"].astype(float)
price = close.to_numpy(copy=True)
n = len(price)

# CMO-based volatility-adjusted moving average (VAR).  Missing warm-up CMO
# values intentionally use the previous VAR value, keeping the series causal.
delta = close.diff()
up = delta.clip(lower=0.0)
down = (-delta).clip(lower=0.0)
up_sum = up.rolling(var_length, min_periods=var_length).sum().to_numpy()
down_sum = down.rolling(var_length, min_periods=var_length).sum().to_numpy()
denominator = up_sum + down_sum
cmo = np.divide(
    up_sum - down_sum,
    denominator,
    out=np.zeros(n, dtype=float),
    where=np.isfinite(denominator) & (denominator > 0.0),
)

var = np.full(n, np.nan, dtype=float)
if n:
    first_finite = np.flatnonzero(np.isfinite(price))
    if len(first_finite):
        first = int(first_finite[0])
        var[first] = price[first]
        alpha_base = 2.0 / (length + 1.0)
        for i in range(first + 1, n):
            if not np.isfinite(price[i]):
                var[i] = var[i - 1]
                continue
            adaptive_alpha = float(np.clip(alpha_base * abs(cmo[i]), 0.0, 1.0))
            var[i] = adaptive_alpha * price[i] + (1.0 - adaptive_alpha) * var[i - 1]

base_up = (base + percent) / base
base_down = (base - percent) / base
fark = var * percent * 0.01
long_stop = var - fark
short_stop = var + fark
trend = np.ones(n, dtype=float)
mt = np.full(n, np.nan, dtype=float)
ott = np.full(n, np.nan, dtype=float)

for i in range(n):
    if not np.isfinite(var[i]):
        if i:
            trend[i] = trend[i - 1]
        continue

    if i:
        previous_long = long_stop[i - 1]
        previous_short = short_stop[i - 1]
        if np.isfinite(previous_long) and var[i] > previous_long:
            long_stop[i] = max(long_stop[i], previous_long)
        if np.isfinite(previous_short) and var[i] < previous_short:
            short_stop[i] = min(short_stop[i], previous_short)

        previous_direction = trend[i - 1]
        if previous_direction < 0 and var[i] > previous_short:
            trend[i] = 1.0
        elif previous_direction > 0 and var[i] < previous_long:
            trend[i] = -1.0
        else:
            trend[i] = previous_direction

    mt[i] = long_stop[i] if trend[i] > 0 else short_stop[i]
    if np.isfinite(mt[i]):
        ott[i] = mt[i] * (base_up if var[i] > mt[i] else base_down)

previous_ott = np.concatenate(([np.nan], ott[:-1]))
previous_mt = np.concatenate(([np.nan], mt[:-1]))
buy = (
    np.isfinite(ott) & np.isfinite(mt) & np.isfinite(previous_ott) & np.isfinite(previous_mt)
    & (previous_ott <= previous_mt) & (ott > mt)
)
sell = (
    np.isfinite(ott) & np.isfinite(mt) & np.isfinite(previous_ott) & np.isfinite(previous_mt)
    & (previous_ott >= previous_mt) & (ott < mt)
)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low = df["low"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
buy_marks = [float(low[i]) * 0.995 if buy[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if sell[i] and np.isfinite(high[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "VAR", "data": plot_list(var), "color": "#42A5F5", "overlay": True},
        {"name": "MT", "data": plot_list(mt), "color": "#FFA726", "overlay": True},
        {"name": "OTT", "data": plot_list(ott), "color": "#AB47BC", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "OTT+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "OTT-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
