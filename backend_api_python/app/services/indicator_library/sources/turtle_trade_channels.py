# ============================================================
# [Default] Turtle Trade Channels
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Donchian-style entry and exit channels use only completed prior bars, avoiding
# look-ahead in the plotted breakout thresholds.
# ============================================================

my_indicator_name = "[Default] Turtle Trade Channels"
my_indicator_description = "Prior-bar breakout and exit channels inspired by Turtle trading rules."

# @param entry_length int 20 Entry channel lookback range=5:100:1
# @param exit_length int 10 Exit channel lookback range=2:50:1

entry_length = max(2, int(params.get("entry_length", 20)))
exit_length = max(2, int(params.get("exit_length", 10)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
entry_upper = high.rolling(entry_length, min_periods=entry_length).max().shift(1)
entry_lower = low.rolling(entry_length, min_periods=entry_length).min().shift(1)
exit_upper = high.rolling(exit_length, min_periods=exit_length).max().shift(1)
exit_lower = low.rolling(exit_length, min_periods=exit_length).min().shift(1)
cl = close.to_numpy()
long_condition = cl > entry_upper.to_numpy()
short_condition = cl < entry_lower.to_numpy()
long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])
short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])
long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(len(df))]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(len(df))]

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Entry Upper", "data": plot_list(entry_upper), "color": "#26A69A", "overlay": True},
        {"name": "Entry Lower", "data": plot_list(entry_lower), "color": "#EF5350", "overlay": True},
        {"name": "Exit Upper", "data": plot_list(exit_upper), "color": "#80CBC4", "overlay": True},
        {"name": "Exit Lower", "data": plot_list(exit_lower), "color": "#EF9A9A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Turtle+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "Turtle-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
