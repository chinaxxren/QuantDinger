"""Reviewed backend calculation for the connors_rsi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _wilder, np, pd


def _connors_rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 3, minimum=2, maximum=50)
    streak_period = _integer(params, "streak_rsi_period", 2, minimum=2, maximum=50)
    rank_period = _integer(params, "rank_period", 100, minimum=5, maximum=200)
    close = _close(df)

    def rsi(values: pd.Series, period: int) -> pd.Series:
        delta = values.diff()
        gain = _wilder(delta.clip(lower=0).fillna(0), period)
        loss = _wilder((-delta.clip(upper=0)).fillna(0), period)
        return (100 * gain / (gain + loss).replace(0, np.nan)).fillna(50).clip(0, 100)

    change = close.diff().to_numpy()
    streak_values = np.zeros(len(df))
    for index in range(1, len(df)):
        streak_values[index] = (
            (streak_values[index - 1] + 1 if streak_values[index - 1] > 0 else 1)
            if change[index] > 0
            else (streak_values[index - 1] - 1 if streak_values[index - 1] < 0 else -1)
            if change[index] < 0
            else 0
        )
    streak_rsi = rsi(pd.Series(streak_values, index=df.index), streak_period)
    returns = close.pct_change(fill_method=None).to_numpy() * 100
    rank = np.full(len(df), np.nan)
    for index in range(rank_period + 1, len(df)):
        prior = returns[index - rank_period : index]
        if np.isfinite(returns[index]) and np.isfinite(prior).all():
            rank[index] = 100 * np.sum(prior < returns[index]) / rank_period
    values = (rsi(close, rsi_period).to_numpy() + streak_rsi.to_numpy() + rank) / 3
    return _output("Connors RSI", [_line("connors_rsi", "Connors RSI", values, color="#7e57c2")])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Connors RSI\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Averages RSI of price, RSI of consecutive up/down streak length, and the\n"
    "# percentile rank of the current one-bar return versus prior returns only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Connors RSI"\n'
    'my_indicator_description = "Composite short-term oscillator combining price RSI, streak RSI, and return rank."\n'
    "\n"
    "# @param rsi_period int 3 Price RSI period range=2:50:1\n"
    "# @param streak_rsi_period int 2 Streak RSI period range=2:50:1\n"
    "# @param rank_period int 100 Prior-return ranking period range=5:200:1\n"
    "\n"
    'rsi_period = max(2, int(params.get("rsi_period", 3)))\n'
    'streak_rsi_period = max(2, int(params.get("streak_rsi_period", 2)))\n'
    'rank_period = max(5, int(params.get("rank_period", 100)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "change = close.diff()\n"
    "\n"
    "def calculate_rsi(series, period):\n"
    "    delta = series.diff()\n"
    "    gains = delta.clip(lower=0.0)\n"
    "    losses = -delta.clip(upper=0.0)\n"
    "    average_gain = gains.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    average_loss = losses.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    total = average_gain + average_loss\n"
    "    result = 100.0 * average_gain / total.replace(0.0, np.nan)\n"
    "    result = result.where(total != 0.0, 50.0)\n"
    "    return result.clip(0.0, 100.0)\n"
    "\n"
    "streak_values = np.zeros(len(df), dtype=float)\n"
    "change_values = change.to_numpy()\n"
    "for i in range(1, len(df)):\n"
    "    if not np.isfinite(change_values[i]):\n"
    "        streak_values[i] = 0.0\n"
    "    elif change_values[i] > 0.0:\n"
    "        streak_values[i] = streak_values[i - 1] + 1.0 if streak_values[i - 1] > 0.0 else 1.0\n"
    "    elif change_values[i] < 0.0:\n"
    "        streak_values[i] = streak_values[i - 1] - 1.0 if streak_values[i - 1] < 0.0 else -1.0\n"
    "    else:\n"
    "        streak_values[i] = 0.0\n"
    "streak = pd.Series(streak_values, index=df.index)\n"
    "price_rsi = calculate_rsi(close, rsi_period)\n"
    "streak_rsi = calculate_rsi(streak, streak_rsi_period)\n"
    "returns = close.pct_change(fill_method=None) * 100.0\n"
    "return_values = returns.to_numpy()\n"
    "percent_rank = np.full(len(df), np.nan)\n"
    "for i in range(rank_period + 1, len(df)):\n"
    "    current = return_values[i]\n"
    "    prior = return_values[i - rank_period:i]\n"
    "    if np.isfinite(current) and np.isfinite(prior).all():\n"
    "        percent_rank[i] = 100.0 * float(np.sum(prior < current)) / rank_period\n"
    "connors = (price_rsi.to_numpy() + streak_rsi.to_numpy() + percent_rank) / 3.0\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Connors RSI", "data": plot_list(connors), "color": "#7E57C2", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _connors_rsi
