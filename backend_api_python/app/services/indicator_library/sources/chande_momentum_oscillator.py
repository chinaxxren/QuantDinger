# ============================================================
# [Default] Chande Momentum Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Normalizes rolling gains and losses into a bounded momentum oscillator.
# The rolling windows are trailing and include only the current and past bars.
# ============================================================

my_indicator_name = "[Default] Chande Momentum Oscillator"
my_indicator_description = "Bounded momentum oscillator based on rolling gains and losses."

# @param period int 14 Rolling momentum period range=2:200:1

period = max(2, int(params.get("period", 14)))

df = df.copy()
change = df["close"].astype(float).diff()
gain = change.clip(lower=0.0)
loss = -change.clip(upper=0.0)
gain_sum = gain.rolling(period, min_periods=period).sum()
loss_sum = loss.rolling(period, min_periods=period).sum()
denominator = gain_sum + loss_sum
cmo = 100.0 * (gain_sum - loss_sum) / denominator.replace(0.0, np.nan)
cmo = cmo.where(denominator != 0.0, 0.0).clip(-100.0, 100.0)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "CMO", "data": plot_list(cmo), "color": "#7E57C2", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
