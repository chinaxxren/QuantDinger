"""Chart-only source for the chande_momentum_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Chande Momentum Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Normalizes rolling gains and losses into a bounded momentum oscillator.\n"
    "# The rolling windows are trailing and include only the current and past bars.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Chande Momentum Oscillator"\n'
    'my_indicator_description = "Bounded momentum oscillator based on rolling gains and losses."\n'
    "\n"
    "# @param period int 14 Rolling momentum period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'change = df["close"].astype(float).diff()\n'
    "gain = change.clip(lower=0.0)\n"
    "loss = -change.clip(upper=0.0)\n"
    "gain_sum = gain.rolling(period, min_periods=period).sum()\n"
    "loss_sum = loss.rolling(period, min_periods=period).sum()\n"
    "denominator = gain_sum + loss_sum\n"
    "cmo = 100.0 * (gain_sum - loss_sum) / denominator.replace(0.0, np.nan)\n"
    "cmo = cmo.where(denominator != 0.0, 0.0).clip(-100.0, 100.0)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "CMO", "data": plot_list(cmo), "color": "#7E57C2", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
