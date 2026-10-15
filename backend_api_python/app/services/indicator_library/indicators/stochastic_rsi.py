"""Reviewed backend calculation for the stochastic_rsi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _rsi_series, np, pd


def _stochastic_rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 14, minimum=2, maximum=100)
    stochastic_period = _integer(params, "stochastic_period", 14, minimum=2, maximum=100)
    k_period = _integer(params, "k_period", 3, minimum=1, maximum=50)
    d_period = _integer(params, "d_period", 3, minimum=1, maximum=50)
    rsi = _rsi_series(_close(df), rsi_period)
    rsi_low = rsi.rolling(stochastic_period, min_periods=stochastic_period).min()
    rsi_high = rsi.rolling(stochastic_period, min_periods=stochastic_period).max()
    rsi_range = rsi_high - rsi_low
    stoch = (rsi - rsi_low) / rsi_range.replace(0, np.nan)
    stoch = stoch.mask((rsi_range == 0) & rsi.notna(), 0.5)
    percent_k = stoch.rolling(k_period, min_periods=k_period).mean() * 100
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return _output(
        "Stochastic RSI",
        [
            _line("stoch_rsi_k", "%K", percent_k, color="#2962ff"),
            _line("stoch_rsi_d", "%D", percent_d, color="#ff6d00"),
        ],
    )


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Stochastic RSI\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Applies a stochastic normalization to RSI. The result is bounded between\n"
    "# zero and one and uses only trailing observations.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Stochastic RSI"\n'
    'my_indicator_description = "Stochastic normalization of RSI with smoothed %K and %D lines."\n'
    "\n"
    "# @param rsi_period int 14 RSI lookback period range=2:100:1\n"
    "# @param stochastic_period int 14 Stochastic normalization period range=2:100:1\n"
    "# @param k_period int 3 %K smoothing period range=1:50:1\n"
    "# @param d_period int 3 %D smoothing period range=1:50:1\n"
    "\n"
    'rsi_period = max(2, int(params.get("rsi_period", 14)))\n'
    'stochastic_period = max(2, int(params.get("stochastic_period", 14)))\n'
    'k_period = max(1, int(params.get("k_period", 3)))\n'
    'd_period = max(1, int(params.get("d_period", 3)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "delta = close.diff()\n"
    "gains = delta.clip(lower=0.0)\n"
    "losses = (-delta.clip(upper=0.0))\n"
    "avg_gain = gains.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "avg_loss = losses.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)\n"
    "rsi = (100.0 - 100.0 / (1.0 + relative_strength)).where(avg_loss != 0.0, 100.0)\n"
    "rsi_low = rsi.rolling(stochastic_period, min_periods=stochastic_period).min()\n"
    "rsi_high = rsi.rolling(stochastic_period, min_periods=stochastic_period).max()\n"
    "stoch_range = (rsi_high - rsi_low).replace(0.0, np.nan)\n"
    "stoch_rsi = ((rsi - rsi_low) / stoch_range).where(stoch_range != 0.0, 0.5)\n"
    "k = stoch_rsi.rolling(k_period, min_periods=k_period).mean()\n"
    "d = k.rolling(d_period, min_periods=d_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "%K", "data": plot_list(k), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "%D", "data": plot_list(d), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _stochastic_rsi
