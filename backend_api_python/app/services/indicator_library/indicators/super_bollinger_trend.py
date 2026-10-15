"""Chart-only source for the super_bollinger_trend indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] SuperBollingerTrend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A causal Bollinger-band trend filter with separated trend lines,\n"
    "# breakout/reversal markers, optional zigzag-style turning points, and an\n"
    "# optional take-profit reference. It is chart-only and never submits orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] SuperBollingerTrend"\n'
    "my_indicator_description = (\n"
    '    "Causal Bollinger trend bands with zigzag-style turning points and "\n'
    '    "optional take-profit reference."\n'
    ")\n"
    "\n"
    "# @param prd int 12 Bollinger lookback range=2:200:1\n"
    "# @param mult float 2.0 Bollinger deviation multiplier range=0.1:10.0:0.1\n"
    "# @param show_zigzag bool True Show causal turning-point line\n"
    "# @param signal str Signal Signal mode: Signal or ZigZag\n"
    "# @param dev str ZigZag Signal deviation mode: ZigZag or Bollinger\n"
    "# @param show_tp bool False Show take-profit reference\n"
    "# @param tp_type str Median Take-profit type: Median or Basis\n"
    "# @param show_table bool False Retained for source compatibility\n"
    "\n"
    'prd = max(2, int(params.get("prd", 12)))\n'
    'mult = max(0.05, float(params.get("mult", 2.0)))\n'
    'show_zigzag = bool(params.get("show_zigzag", True))\n'
    'signal_mode = str(params.get("signal", "Signal")).strip().lower()\n'
    'dev_mode = str(params.get("dev", "ZigZag")).strip().lower()\n'
    'show_tp = bool(params.get("show_tp", False))\n'
    'tp_type = str(params.get("tp_type", "Median")).strip().lower()\n'
    "\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "\n"
    "basis_series = close.rolling(prd, min_periods=prd).mean()\n"
    "std_series = close.rolling(prd, min_periods=prd).std(ddof=0)\n"
    "upper_series = basis_series + mult * std_series\n"
    "lower_series = basis_series - mult * std_series\n"
    "\n"
    "basis = basis_series.to_numpy(dtype=float)\n"
    "upper = upper_series.to_numpy(dtype=float)\n"
    "lower = lower_series.to_numpy(dtype=float)\n"
    "close_values = close.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "\n"
    "trend = np.zeros(n, dtype=np.int8)\n"
    "sbt = np.full(n, np.nan, dtype=float)\n"
    "for i in range(n):\n"
    "    if not np.isfinite(close_values[i]) or not np.isfinite(upper[i]) or not np.isfinite(lower[i]):\n"
    "        if i > 0:\n"
    "            trend[i] = trend[i - 1]\n"
    "            sbt[i] = sbt[i - 1]\n"
    "        continue\n"
    "\n"
    "    previous_trend = trend[i - 1] if i else 0\n"
    "    if close_values[i] > upper[i]:\n"
    "        trend[i] = 1\n"
    "    elif close_values[i] < lower[i]:\n"
    "        trend[i] = -1\n"
    "    else:\n"
    "        trend[i] = previous_trend\n"
    "\n"
    "    if trend[i] > 0:\n"
    "        sbt[i] = lower[i]\n"
    "    elif trend[i] < 0:\n"
    "        sbt[i] = upper[i]\n"
    "    else:\n"
    "        sbt[i] = basis[i]\n"
    "\n"
    "# Keep each colored line continuous across a confirmed reversal bar.\n"
    "sbt_up = np.where(trend > 0, sbt, np.nan)\n"
    "sbt_down = np.where(trend < 0, sbt, np.nan)\n"
    "for i in range(1, n):\n"
    "    if trend[i] > 0 and trend[i - 1] < 0:\n"
    "        sbt_up[i - 1] = sbt[i - 1]\n"
    "        sbt_up[i] = sbt[i]\n"
    "    elif trend[i] < 0 and trend[i - 1] > 0:\n"
    "        sbt_down[i - 1] = sbt[i - 1]\n"
    "        sbt_down[i] = sbt[i]\n"
    "\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "trend_buy = (trend == 1) & (previous_trend == -1)\n"
    "trend_sell = (trend == -1) & (previous_trend == 1)\n"
    "\n"
    "# A causal zigzag approximation: retain the latest close at a trend flip.\n"
    "# No right-side pivot confirmation is used, so future bars cannot alter history.\n"
    "zigzag = np.full(n, np.nan, dtype=float)\n"
    "last_turn = np.nan\n"
    "for i in range(n):\n"
    "    if trend[i] != 0 and trend[i] != previous_trend[i]:\n"
    "        last_turn = close_values[i]\n"
    "    if np.isfinite(last_turn):\n"
    "        zigzag[i] = last_turn\n"
    "\n"
    "zigzag_diff = np.full(n, np.nan, dtype=float)\n"
    "for i in range(1, n):\n"
    "    if np.isfinite(zigzag[i]) and np.isfinite(zigzag[i - 1]):\n"
    "        zigzag_diff[i] = zigzag[i] - zigzag[i - 1]\n"
    "zigzag_delta = np.abs(zigzag_diff)\n"
    "\n"
    'if signal_mode == "zigzag":\n'
    "    buy = trend_buy & (zigzag_diff > 0)\n"
    "    sell = trend_sell & (zigzag_diff < 0)\n"
    'elif dev_mode == "bollinger":\n'
    "    buy = (close_values > upper) & (previous_trend <= 0)\n"
    "    sell = (close_values < lower) & (previous_trend >= 0)\n"
    "else:\n"
    "    buy = trend_buy\n"
    "    sell = trend_sell\n"
    "\n"
    'if tp_type == "basis":\n'
    "    take_profit = basis.copy()\n"
    "else:\n"
    "    take_profit = ((upper + lower) / 2.0).astype(float)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "plots = [\n"
    '    {"name": "SBT Up", "data": plot_list(sbt_up), "color": "#00BCD4", "overlay": True},\n'
    '    {"name": "SBT Down", "data": plot_list(sbt_down), "color": "#FF5252", "overlay": True},\n'
    "]\n"
    "if show_zigzag:\n"
    '    plots.append({"name": "ZigZag", "data": plot_list(zigzag), "color": "#9E9E9E", "overlay": True})\n'
    "if show_tp:\n"
    '    plots.append({"name": "Take Profit", "data": plot_list(take_profit), "color": "#FF9800", "overlay": True})\n'
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": plots,\n'
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "Buy",\n'
    '            "data": [\n'
    "                float(low_values[i]) * 0.995\n"
    "                if buy[i] and np.isfinite(low_values[i])\n"
    "                else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "Sell",\n'
    '            "data": [\n'
    "                float(high_values[i]) * 1.005\n"
    "                if sell[i] and np.isfinite(high_values[i])\n"
    "                else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#FF5252",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "basis": plot_list(basis),\n'
    '        "upper": plot_list(upper),\n'
    '        "lower": plot_list(lower),\n'
    '        "sbt": plot_list(sbt),\n'
    '        "zigzag_diff": plot_list(zigzag_diff),\n'
    '        "zigzag_delta": plot_list(zigzag_delta),\n'
    '        "trend": [int(value) if value else None for value in trend],\n'
    '        "causal": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
