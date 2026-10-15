"""Chart-only source for the know_sure_thing indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Know Sure Thing\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Weighted sum of four smoothed rate-of-change series. Each ROC, average,\n"
    "# and signal uses trailing data only, keeping all historical values causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Know Sure Thing"\n'
    'my_indicator_description = "Multi-horizon momentum oscillator with a signal line."\n'
    "\n"
    "# @param roc1_period int 10 First ROC period range=2:100:1\n"
    "# @param roc2_period int 15 Second ROC period range=2:150:1\n"
    "# @param roc3_period int 20 Third ROC period range=2:200:1\n"
    "# @param roc4_period int 30 Fourth ROC period range=2:250:1\n"
    "# @param signal_period int 9 Signal SMA period range=2:100:1\n"
    "\n"
    "roc_periods = [\n"
    '    max(2, int(params.get("roc1_period", 10))),\n'
    '    max(2, int(params.get("roc2_period", 15))),\n'
    '    max(2, int(params.get("roc3_period", 20))),\n'
    '    max(2, int(params.get("roc4_period", 30))),\n'
    "]\n"
    'signal_period = max(2, int(params.get("signal_period", 9)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "smoothed_rocs = []\n"
    "for roc_period in roc_periods:\n"
    "    base = close.shift(roc_period).replace(0.0, np.nan)\n"
    "    roc = 100.0 * (close / base - 1.0)\n"
    "    smoothed_rocs.append(roc.rolling(roc_period, min_periods=roc_period).mean())\n"
    "kst = (\n"
    "    smoothed_rocs[0]\n"
    "    + 2.0 * smoothed_rocs[1]\n"
    "    + 3.0 * smoothed_rocs[2]\n"
    "    + 4.0 * smoothed_rocs[3]\n"
    ")\n"
    "signal = kst.rolling(signal_period, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "KST", "data": plot_list(kst), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
