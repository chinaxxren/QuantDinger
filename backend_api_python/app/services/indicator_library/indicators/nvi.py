"""Chart-only source for the nvi indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# Negative Volume Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Updates the cumulative index on bars where volume is no greater than the\n"
    "# previous bar, using the close-to-close percentage return.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "Negative Volume Index"\n'
    'my_indicator_description = "Cumulative price index updated on non-increasing-volume bars."\n'
    "\n"
    'close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)\n'
    'volume = pd.to_numeric(df["volume"], errors="coerce").to_numpy(dtype=float)\n'
    "nvi = np.full(len(df), np.nan, dtype=float)\n"
    "previous_index = 1000.0\n"
    "\n"
    "for index in range(1, len(df)):\n"
    "    previous_close = close[index - 1]\n"
    "    current_close = close[index]\n"
    "    previous_volume = volume[index - 1]\n"
    "    current_volume = volume[index]\n"
    "    if not np.isfinite([previous_close, current_close, previous_volume, current_volume]).all():\n"
    "        continue\n"
    "    if previous_close == 0:\n"
    "        continue\n"
    "    if current_volume <= previous_volume:\n"
    "        previous_index *= 1.0 + (current_close - previous_close) / previous_close\n"
    "    nvi[index] = previous_index\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [{\n'
    '        "key": "nvi",\n'
    '        "title": "NVI",\n'
    '        "data": nvi.tolist(),\n'
    '        "color": "#26a69a",\n'
    '        "overlay": False,\n'
    "    }],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
