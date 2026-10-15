"""Chart-only source for the flawless_victory_strategy indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Flawless Victory Strategy\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Bollinger mean-reversion bands with RSI/MFI filters. The source is\n"
    "# intentionally chart-only: it exposes entry/exit markers and visual risk\n"
    "# levels but never submits orders or mutates a trading position.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Flawless Victory Strategy"\n'
    "my_indicator_description = (\n"
    '    "Bollinger mean-reversion bands with RSI/MFI filters and chart-only "\n'
    '    "long-entry, exit, stop-loss, and take-profit markers."\n'
    ")\n"
    "\n"
    "# @param version string v1 Version: v1, v2, or v3\n"
    "# @param bb_length int 20 Bollinger period (v2 uses 17 by default) range=2:100:1\n"
    "# @param bb_multiplier float 1.0 Bollinger standard deviation multiplier range=0.1:4.0:0.1\n"
    "# @param rsi_length int 14 RSI period range=2:100:1\n"
    "# @param mfi_length int 14 MFI period range=2:100:1\n"
    "# @param v1_rsi_lower float 42.0 v1 entry RSI threshold range=0:100:0.1\n"
    "# @param v1_rsi_upper float 70.0 v1 exit RSI threshold range=0:100:0.1\n"
    "# @param v2_rsi_lower float 42.0 v2 entry RSI threshold range=0:100:0.1\n"
    "# @param v2_rsi_upper float 76.0 v2 exit RSI threshold range=0:100:0.1\n"
    "# @param v2_stoploss float 6.604 v2 stop loss percentage range=0:100:0.001\n"
    "# @param v2_takeprofit float 2.328 v2 take profit percentage range=0:100:0.001\n"
    "# @param v3_mfi_lower float 60.0 v3 entry MFI threshold range=0:100:0.1\n"
    "# @param v3_rsi_upper float 65.0 v3 exit RSI threshold range=0:100:0.1\n"
    "# @param v3_mfi_upper float 64.0 v3 exit MFI threshold range=0:100:0.1\n"
    "# @param v3_stoploss float 8.882 v3 stop loss percentage range=0:100:0.001\n"
    "# @param v3_takeprofit float 2.317 v3 take profit percentage range=0:100:0.001\n"
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, str):\n"
    "        lowered = value.strip().lower()\n"
    '        if lowered in ("false", "0", "no", "off"):\n'
    "            return False\n"
    '        if lowered in ("true", "1", "yes", "on"):\n'
    "            return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    'version = str(params.get("version", "v1")).strip().lower()\n'
    'if version not in ("v1", "v2", "v3"):\n'
    '    version = "v1"\n'
    "\n"
    'configured_bb_length = max(2, int(params.get("bb_length", 20)))\n'
    'if "bb_length" not in params:\n'
    '    configured_bb_length = 17 if version == "v2" else 20\n'
    "bb_length = configured_bb_length\n"
    'bb_multiplier = max(0.1, float(params.get("bb_multiplier", 1.0)))\n'
    'rsi_length = max(2, int(params.get("rsi_length", 14)))\n'
    'mfi_length = max(2, int(params.get("mfi_length", 14)))\n'
    "\n"
    'v1_rsi_lower = float(params.get("v1_rsi_lower", 42.0))\n'
    'v1_rsi_upper = float(params.get("v1_rsi_upper", 70.0))\n'
    'v2_rsi_lower = float(params.get("v2_rsi_lower", 42.0))\n'
    'v2_rsi_upper = float(params.get("v2_rsi_upper", 76.0))\n'
    'v2_stoploss = max(0.0, float(params.get("v2_stoploss", 6.604)))\n'
    'v2_takeprofit = max(0.0, float(params.get("v2_takeprofit", 2.328)))\n'
    'v3_mfi_lower = float(params.get("v3_mfi_lower", 60.0))\n'
    'v3_rsi_upper = float(params.get("v3_rsi_upper", 65.0))\n'
    'v3_mfi_upper = float(params.get("v3_mfi_upper", 64.0))\n'
    'v3_stoploss = max(0.0, float(params.get("v3_stoploss", 8.882)))\n'
    'v3_takeprofit = max(0.0, float(params.get("v3_takeprofit", 2.317)))\n'
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "def rsi_wilder(values, length):\n"
    "    delta = values.diff()\n"
    "    gain = delta.clip(lower=0.0)\n"
    "    loss = (-delta).clip(lower=0.0)\n"
    "    average_gain = gain.ewm(\n"
    "        alpha=1.0 / length, adjust=False, min_periods=length\n"
    "    ).mean()\n"
    "    average_loss = loss.ewm(\n"
    "        alpha=1.0 / length, adjust=False, min_periods=length\n"
    "    ).mean()\n"
    "    gain_values = average_gain.to_numpy(dtype=float)\n"
    "    loss_values = average_loss.to_numpy(dtype=float)\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    valid = np.isfinite(gain_values) & np.isfinite(loss_values)\n"
    "    nonzero_loss = valid & (loss_values > 0.0)\n"
    "    result[nonzero_loss] = 100.0 - (100.0 / (1.0 + gain_values[nonzero_loss] / loss_values[nonzero_loss]))\n"
    "    result[valid & (loss_values <= 0.0) & (gain_values > 0.0)] = 100.0\n"
    "    result[valid & (loss_values <= 0.0) & (gain_values <= 0.0)] = 50.0\n"
    "    return result\n"
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float)\n'
    "\n"
    "basis_series = close.rolling(bb_length, min_periods=bb_length).mean()\n"
    "std_series = close.rolling(bb_length, min_periods=bb_length).std(ddof=0)\n"
    "basis = basis_series.to_numpy(dtype=float)\n"
    "upper = (basis_series + bb_multiplier * std_series).to_numpy(dtype=float)\n"
    "lower = (basis_series - bb_multiplier * std_series).to_numpy(dtype=float)\n"
    "\n"
    "rsi = rsi_wilder(close, rsi_length)\n"
    "typical_price = (high + low + close) / 3.0\n"
    "money_flow = typical_price * volume\n"
    "price_delta = typical_price.diff().to_numpy(dtype=float)\n"
    "money_flow_values = money_flow.to_numpy(dtype=float)\n"
    "positive_flow = np.where(price_delta > 0.0, money_flow_values, 0.0)\n"
    "negative_flow = np.where(price_delta < 0.0, money_flow_values, 0.0)\n"
    "positive_sum = pd.Series(positive_flow, index=df.index).rolling(\n"
    "    mfi_length, min_periods=mfi_length\n"
    ").sum().to_numpy(dtype=float)\n"
    "negative_sum = pd.Series(negative_flow, index=df.index).rolling(\n"
    "    mfi_length, min_periods=mfi_length\n"
    ").sum().to_numpy(dtype=float)\n"
    "mfi = np.full(len(df), np.nan, dtype=float)\n"
    "valid_mfi = np.isfinite(positive_sum) & np.isfinite(negative_sum)\n"
    "nonzero_negative = valid_mfi & (negative_sum > 0.0)\n"
    "mfi[nonzero_negative] = 100.0 - (\n"
    "    100.0 / (1.0 + positive_sum[nonzero_negative] / negative_sum[nonzero_negative])\n"
    ")\n"
    "mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum > 0.0)] = 100.0\n"
    "mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum <= 0.0)] = 50.0\n"
    "\n"
    "close_values = close.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "\n"
    'if version == "v2":\n'
    "    entry_condition = (close_values < lower) & (rsi > v2_rsi_lower)\n"
    "    exit_condition = (close_values > upper) & (rsi > v2_rsi_upper)\n"
    "    stoploss_percent = v2_stoploss\n"
    "    takeprofit_percent = v2_takeprofit\n"
    'elif version == "v3":\n'
    "    entry_condition = (close_values < lower) & (mfi < v3_mfi_lower)\n"
    "    exit_condition = (\n"
    "        (close_values > upper) & (rsi > v3_rsi_upper) & (mfi > v3_mfi_upper)\n"
    "    )\n"
    "    stoploss_percent = v3_stoploss\n"
    "    takeprofit_percent = v3_takeprofit\n"
    "else:\n"
    "    entry_condition = (close_values < lower) & (rsi > v1_rsi_lower)\n"
    "    exit_condition = (close_values > upper) & (rsi > v1_rsi_upper)\n"
    "    stoploss_percent = 0.0\n"
    "    takeprofit_percent = 0.0\n"
    "\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "exitlong_signal = np.zeros(n, dtype=bool)\n"
    "stoploss = np.full(n, np.nan, dtype=float)\n"
    "takeprofit = np.full(n, np.nan, dtype=float)\n"
    "active_entry = np.nan\n"
    "active_stoploss = np.nan\n"
    "active_takeprofit = np.nan\n"
    "active = False\n"
    "\n"
    "for i in range(n):\n"
    "    if active:\n"
    "        stop_hit = (\n"
    "            np.isfinite(active_stoploss)\n"
    "            and np.isfinite(low_values[i])\n"
    "            and low_values[i] <= active_stoploss\n"
    "        )\n"
    "        takeprofit_hit = (\n"
    "            np.isfinite(active_takeprofit)\n"
    "            and np.isfinite(high_values[i])\n"
    "            and high_values[i] >= active_takeprofit\n"
    "        )\n"
    "        exit_hit = bool(exit_condition[i]) or stop_hit or takeprofit_hit\n"
    "        stoploss[i] = active_stoploss\n"
    "        takeprofit[i] = active_takeprofit\n"
    "        if exit_hit:\n"
    "            exitlong_signal[i] = True\n"
    "            active = False\n"
    "            active_entry = np.nan\n"
    "            active_stoploss = np.nan\n"
    "            active_takeprofit = np.nan\n"
    "        continue\n"
    "\n"
    "    if bool(entry_condition[i]) and np.isfinite(close_values[i]):\n"
    "        long_signal[i] = True\n"
    "        active = True\n"
    "        active_entry = close_values[i]\n"
    '        if version != "v1":\n'
    "            active_stoploss = active_entry * (1.0 - stoploss_percent / 100.0)\n"
    "            active_takeprofit = active_entry * (1.0 + takeprofit_percent / 100.0)\n"
    "            stoploss[i] = active_stoploss\n"
    "            takeprofit[i] = active_takeprofit\n"
    "\n"
    "# Keep the unused entry variable explicit for source-level reviewers and safe\n"
    "# execution validation; it is only used as the basis for chart risk levels.\n"
    "_ = active_entry\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Basis", "data": plot_list(basis), "color": "#9E9E9E", "overlay": True},\n'
    '        {"name": "Upper", "data": plot_list(upper), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "Lower", "data": plot_list(lower), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "Stop Loss", "data": plot_list(stoploss), "color": "#EF5350", "overlay": True},\n'
    '        {"name": "Take Profit", "data": plot_list(takeprofit), "color": "#26A69A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "Long Entry",\n'
    '            "data": [\n'
    "                float(low_values[i]) * 0.995\n"
    "                if long_signal[i] and np.isfinite(low_values[i])\n"
    "                else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "Long Exit",\n'
    '            "data": [\n'
    "                float(high_values[i]) * 1.005\n"
    "                if exitlong_signal[i] and np.isfinite(high_values[i])\n"
    "                else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#FF5252",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "version": version,\n'
    '        "bb_length": bb_length,\n'
    '        "basis": plot_list(basis),\n'
    '        "upper": plot_list(upper),\n'
    '        "lower": plot_list(lower),\n'
    '        "rsi": plot_list(rsi),\n'
    '        "mfi": plot_list(mfi),\n'
    '        "stoploss": plot_list(stoploss),\n'
    '        "takeprofit": plot_list(takeprofit),\n'
    '        "causal": True,\n'
    '        "chart_only": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
