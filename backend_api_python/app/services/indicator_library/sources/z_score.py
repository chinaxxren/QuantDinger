# ============================================================
# Z-Score
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Measures how many population standard deviations the close is from its
# trailing simple moving average. A flat window has a mathematically defined
# score of zero.
# ============================================================

my_indicator_name = "Z-Score"
my_indicator_description = "Standard-deviation distance of price from its rolling mean."

# @param period int 20 Rolling calculation period range=2:300:1

period = int(params.get("period", 20))
close = pd.to_numeric(df["close"], errors="coerce")
middle = close.rolling(period, min_periods=period).mean()
deviation = close.rolling(period, min_periods=period).std(ddof=0)
z_score = (close - middle) / deviation.replace(0.0, np.nan)
z_score = z_score.mask((deviation == 0.0) & (close.notna()), 0.0)

output = {
    "name": my_indicator_name,
    "plots": [{
        "key": "z_score",
        "title": f"Z-Score({period})",
        "data": z_score.tolist(),
        "color": "#2962ff",
        "overlay": False,
    }],
    "signals": [],
    "layers": [],
}
