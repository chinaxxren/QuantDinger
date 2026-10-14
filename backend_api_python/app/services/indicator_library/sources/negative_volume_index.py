# ============================================================
# Negative Volume Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Updates the cumulative index on bars where volume is no greater than the
# previous bar, using the close-to-close percentage return.
# ============================================================

my_indicator_name = "Negative Volume Index"
my_indicator_description = "Cumulative price index updated on non-increasing-volume bars."

close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
volume = pd.to_numeric(df["volume"], errors="coerce").to_numpy(dtype=float)
nvi = np.full(len(df), np.nan, dtype=float)
previous_index = 1000.0

for index in range(1, len(df)):
    previous_close = close[index - 1]
    current_close = close[index]
    previous_volume = volume[index - 1]
    current_volume = volume[index]
    if not np.isfinite([previous_close, current_close, previous_volume, current_volume]).all():
        continue
    if previous_close == 0:
        continue
    if current_volume <= previous_volume:
        previous_index *= 1.0 + (current_close - previous_close) / previous_close
    nvi[index] = previous_index

output = {
    "name": my_indicator_name,
    "plots": [{
        "key": "nvi",
        "title": "NVI",
        "data": nvi.tolist(),
        "color": "#26a69a",
        "overlay": False,
    }],
    "signals": [],
    "layers": [],
}
