# ============================================================
# [Default] RSI Momentum
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Wilder-style RSI shown in its own indicator pane. No orders are generated.
# ============================================================

my_indicator_name = "[Default] RSI Momentum"
my_indicator_description = "Wilder RSI momentum oscillator with configurable period."

# @param length int 14 RSI lookback period range=2:50:1

length = max(2, int(params.get("length", 14)))

df = df.copy()
close = df["close"].astype(float)
delta = close.diff()
gain = delta.clip(lower=0.0)
loss = -delta.clip(upper=0.0)
avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)
rsi = 100.0 - (100.0 / (1.0 + relative_strength))
rsi = rsi.where(avg_loss != 0.0, 100.0)
rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RSI", "data": [None if pd.isna(v) else float(v) for v in rsi], "color": "#7E57C2", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
