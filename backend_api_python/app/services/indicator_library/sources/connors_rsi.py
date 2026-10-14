# ============================================================
# [Default] Connors RSI
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Averages RSI of price, RSI of consecutive up/down streak length, and the
# percentile rank of the current one-bar return versus prior returns only.
# ============================================================

my_indicator_name = "[Default] Connors RSI"
my_indicator_description = "Composite short-term oscillator combining price RSI, streak RSI, and return rank."

# @param rsi_period int 3 Price RSI period range=2:50:1
# @param streak_rsi_period int 2 Streak RSI period range=2:50:1
# @param rank_period int 100 Prior-return ranking period range=5:200:1

rsi_period = max(2, int(params.get("rsi_period", 3)))
streak_rsi_period = max(2, int(params.get("streak_rsi_period", 2)))
rank_period = max(5, int(params.get("rank_period", 100)))

df = df.copy()
close = df["close"].astype(float)
change = close.diff()

def calculate_rsi(series, period):
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    average_gain = gains.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    average_loss = losses.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    total = average_gain + average_loss
    result = 100.0 * average_gain / total.replace(0.0, np.nan)
    result = result.where(total != 0.0, 50.0)
    return result.clip(0.0, 100.0)

streak_values = np.zeros(len(df), dtype=float)
change_values = change.to_numpy()
for i in range(1, len(df)):
    if not np.isfinite(change_values[i]):
        streak_values[i] = 0.0
    elif change_values[i] > 0.0:
        streak_values[i] = streak_values[i - 1] + 1.0 if streak_values[i - 1] > 0.0 else 1.0
    elif change_values[i] < 0.0:
        streak_values[i] = streak_values[i - 1] - 1.0 if streak_values[i - 1] < 0.0 else -1.0
    else:
        streak_values[i] = 0.0
streak = pd.Series(streak_values, index=df.index)
price_rsi = calculate_rsi(close, rsi_period)
streak_rsi = calculate_rsi(streak, streak_rsi_period)
returns = close.pct_change(fill_method=None) * 100.0
return_values = returns.to_numpy()
percent_rank = np.full(len(df), np.nan)
for i in range(rank_period + 1, len(df)):
    current = return_values[i]
    prior = return_values[i - rank_period:i]
    if np.isfinite(current) and np.isfinite(prior).all():
        percent_rank[i] = 100.0 * float(np.sum(prior < current)) / rank_period
connors = (price_rsi.to_numpy() + streak_rsi.to_numpy() + percent_rank) / 3.0

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Connors RSI", "data": plot_list(connors), "color": "#7E57C2", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
