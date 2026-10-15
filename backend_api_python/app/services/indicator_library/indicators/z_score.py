"""Chart-only source for the z_score indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# Z-Score\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Measures how many population standard deviations the close is from its\n"
    "# trailing simple moving average. A flat window has a mathematically defined\n"
    "# score of zero.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "Z-Score"\n'
    'my_indicator_description = "Standard-deviation distance of price from its rolling mean."\n'
    "\n"
    "# @param period int 20 Rolling calculation period range=2:300:1\n"
    "\n"
    'period = int(params.get("period", 20))\n'
    'close = pd.to_numeric(df["close"], errors="coerce")\n'
    "middle = close.rolling(period, min_periods=period).mean()\n"
    "deviation = close.rolling(period, min_periods=period).std(ddof=0)\n"
    "z_score = (close - middle) / deviation.replace(0.0, np.nan)\n"
    "z_score = z_score.mask((deviation == 0.0) & (close.notna()), 0.0)\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [{\n'
    '        "key": "z_score",\n'
    '        "title": f"Z-Score({period})",\n'
    '        "data": z_score.tolist(),\n'
    '        "color": "#2962ff",\n'
    '        "overlay": False,\n'
    "    }],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
