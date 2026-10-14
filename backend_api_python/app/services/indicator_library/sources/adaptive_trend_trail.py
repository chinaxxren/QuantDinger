# ============================================================
# [Default] Adaptive Trend Trail
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Multi-factor trend state and adaptive SuperTrend consensus inspired by
# Uptrick's Adaptive Trend Trail. All calculations use current/past bars only.
# Signals and trail levels are visual chart outputs; no orders are submitted.
# ============================================================

my_indicator_name = "[Default] Adaptive Trend Trail"
my_indicator_description = "Multi-factor adaptive trend state with SuperTrend confirmation and chart-only trails/signals."

# @param trend_length int 34 EMA trend baseline length range=5:200:1
# @param momentum_length int 12 Momentum lookback range=2:100:1
# @param sensitivity float 0.35 Signal selectivity range=0.0:1.0:0.05
# @param st_fast_length int 9 Fast SuperTrend ATR length range=2:100:1
# @param st_fast_factor float 1.45 Fast SuperTrend ATR factor range=0.5:5.0:0.05
# @param st_mid_length int 14 Mid SuperTrend ATR length range=2:100:1
# @param st_mid_factor float 1.95 Mid SuperTrend ATR factor range=0.5:6.0:0.05
# @param st_slow_length int 21 Slow SuperTrend ATR length range=2:150:1
# @param st_slow_factor float 2.55 Slow SuperTrend ATR factor range=0.5:8.0:0.05
# @param overlay_mode string Trail Overlay mode: Trail, Bands, or None
# @param trail_size float 1.0 Trail width multiplier range=0.5:2.0:0.05
# @param smoothness int 5 Trail smoothing length range=1:50:1

trend_length = max(5, int(params.get("trend_length", 34)))
momentum_length = max(2, int(params.get("momentum_length", 12)))
sensitivity = min(1.0, max(0.0, float(params.get("sensitivity", 0.35))))
fast_length = max(2, int(params.get("st_fast_length", 9)))
mid_length = max(2, int(params.get("st_mid_length", 14)))
slow_length = max(2, int(params.get("st_slow_length", 21)))
fast_factor = max(0.5, float(params.get("st_fast_factor", 1.45)))
mid_factor = max(0.5, float(params.get("st_mid_factor", 1.95)))
slow_factor = max(0.5, float(params.get("st_slow_factor", 2.55)))
overlay_mode = str(params.get("overlay_mode", "Trail")).strip().lower()
if overlay_mode not in ("trail", "bands", "none"):
    raise ValueError("overlay_mode must be Trail, Bands, or None")
trail_size = min(2.0, max(0.5, float(params.get("trail_size", 1.0))))
smoothness = max(1, int(params.get("smoothness", 5)))

df = df.copy()
open_v = df["open"].astype(float).to_numpy()
high_v = df["high"].astype(float).to_numpy()
low_v = df["low"].astype(float).to_numpy()
close_v = df["close"].astype(float).to_numpy()
n = len(close_v)


def clamp(values, lower_bound, upper_bound):
    return np.clip(values, lower_bound, upper_bound)


def ema(values, span):
    return pd.Series(values, dtype=float).ewm(span=span, adjust=False, ignore_na=True).mean().to_numpy()


def rma(values, period):
    series = pd.Series(values, dtype=float)
    result = np.full(len(series), np.nan, dtype=float)
    if len(series) >= period:
        seed_values = series.to_numpy(dtype=float)
        for idx in range(period - 1, len(series)):
            window = seed_values[idx - period + 1:idx + 1]
            if np.isfinite(window).all():
                result[idx] = float(np.mean(window))
                start = idx + 1
                break
        else:
            start = len(series)
        for idx in range(start, len(series)):
            if np.isfinite(seed_values[idx]) and np.isfinite(result[idx - 1]):
                result[idx] = (result[idx - 1] * (period - 1) + seed_values[idx]) / period
    return result


previous_close = np.concatenate(([np.nan], close_v[:-1])) if n else np.array([], dtype=float)
tr = np.maximum.reduce([
    high_v - low_v,
    np.abs(high_v - previous_close),
    np.abs(low_v - previous_close),
]) if n else np.array([], dtype=float)
tr[~np.isfinite(tr)] = np.nan
atr14 = rma(tr, 14)
safe_atr = np.maximum(np.nan_to_num(atr14, nan=0.0), 1e-9)
basis = ema(close_v, trend_length)

momentum_delta = np.full(n, np.nan, dtype=float)
if n > momentum_length:
    momentum_delta[momentum_length:] = close_v[momentum_length:] - close_v[:-momentum_length]
momentum = np.nan_to_num(ema(momentum_delta, 5), nan=0.0) / safe_atr
distance = (close_v - basis) / safe_atr

# Kaufman-style directional efficiency and choppiness.
eff_length = 10
net_move = np.zeros(n, dtype=float)
travel = np.zeros(n, dtype=float)
if n > eff_length:
    net_move[eff_length:] = np.abs(close_v[eff_length:] - close_v[:-eff_length])
    abs_returns = np.abs(np.diff(close_v))
    rolling_path = pd.Series(np.concatenate(([np.nan], abs_returns))).rolling(eff_length, min_periods=eff_length).sum().to_numpy()
    travel[:] = np.nan_to_num(rolling_path, nan=0.0)
efficiency = np.where(travel > 0.0, clamp(np.divide(net_move, travel, out=np.zeros(n), where=travel > 0.0), 0.0, 1.0), 0.0)
chop = 1.0 - efficiency
close_shift = np.full(n, np.nan, dtype=float)
if n > eff_length:
    close_shift[eff_length:] = close_v[:-eff_length]
eff_direction = np.where(close_v > close_shift, 1.0, np.where(close_v < close_shift, -1.0, 0.0))
eff_direction[:min(eff_length, n)] = 0.0
efficiency_field = efficiency * eff_direction

normal_atr = ema(safe_atr, 50)
vol_ratio = np.divide(safe_atr, normal_atr, out=np.ones(n, dtype=float), where=normal_atr > 0.0)
vol_expansion = clamp(vol_ratio - 1.0, 0.0, 1.25)
vol_deviation = clamp(np.abs(vol_ratio - 1.0), 0.0, 1.50)


def supertrend_direction(src, factors, atr_period):
    atr = rma(tr, atr_period)
    upper_band = src + factors * np.nan_to_num(atr, nan=0.0)
    lower_band = src - factors * np.nan_to_num(atr, nan=0.0)
    direction = np.ones(n, dtype=float)  # +1 bearish, -1 bullish
    start = atr_period + 1
    if start >= n:
        return direction
    for idx in range(start + 1, n):
        if close_v[idx - 1] > lower_band[idx - 1]:
            lower_band[idx] = max(lower_band[idx], lower_band[idx - 1])
        if close_v[idx - 1] < upper_band[idx - 1]:
            upper_band[idx] = min(upper_band[idx], upper_band[idx - 1])
        if direction[idx - 1] > 0:
            direction[idx] = -1.0 if src[idx] > upper_band[idx] else 1.0
        else:
            direction[idx] = 1.0 if src[idx] < lower_band[idx] else -1.0
    return direction

hl2 = (high_v + low_v) / 2.0
fast_dir = supertrend_direction(hl2, fast_factor + chop * 0.25 + vol_expansion * 0.10, fast_length)
mid_dir = supertrend_direction(hl2, mid_factor + chop * 0.35 + vol_expansion * 0.15, mid_length)
slow_dir = supertrend_direction(hl2, slow_factor + chop * 0.45 + vol_expansion * 0.20, slow_length)
fast_bull, mid_bull, slow_bull = fast_dir < 0, mid_dir < 0, slow_dir < 0
fast_bear, mid_bear, slow_bear = fast_dir > 0, mid_dir > 0, slow_dir > 0
bull_votes = fast_bull.astype(int) + mid_bull.astype(int) + slow_bull.astype(int)
bear_votes = fast_bear.astype(int) + mid_bear.astype(int) + slow_bear.astype(int)
required_votes = np.where(chop > 0.70, 3, 2)
bull_st_confirmed = bull_votes >= required_votes
bear_st_confirmed = bear_votes >= required_votes
full_bull_st = bull_votes == 3
full_bear_st = bear_votes == 3

basis_shift3 = np.full(n, np.nan, dtype=float)
slow_center_len = max(10, int(round(trend_length * 0.70)))
slow_center = ema(hl2, slow_center_len)
slow_center_shift3 = np.full(n, np.nan, dtype=float)
if n > 3:
    basis_shift3[3:] = basis[:-3]
    slow_center_shift3[3:] = slow_center[:-3]
slope_field = clamp(np.nan_to_num((basis - basis_shift3) / safe_atr, nan=0.0) / 0.25, -1.0, 1.0)
slow_slope_field = clamp(np.nan_to_num((slow_center - slow_center_shift3) / safe_atr, nan=0.0) / 0.25, -1.0, 1.0)
rsi_delta = pd.Series(close_v).diff()
gain = rsi_delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()
loss = (-rsi_delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()
rsi = 100.0 - 100.0 / (1.0 + np.divide(gain, loss, out=np.ones(n, dtype=float), where=loss > 0.0))
rsi = np.nan_to_num(rsi, nan=50.0)
rsi_field = clamp((rsi - 50.0) / 20.0, -1.0, 1.0)
st_field = (bull_votes - bear_votes) / 3.0
struct_len = max(3, int(round(trend_length * 0.12)))
recent_high = df["high"].astype(float).shift(1).rolling(struct_len, min_periods=struct_len).max().to_numpy()
recent_low = df["low"].astype(float).shift(1).rolling(struct_len, min_periods=struct_len).min().to_numpy()
structure_field = np.where(close_v > recent_high, 1.0, np.where(close_v < recent_low, -1.0, 0.0))
bar_range = np.maximum(high_v - low_v, 1e-9)
body_pressure = (close_v - open_v) / bar_range
close_location = ((close_v - low_v) / bar_range - 0.5) * 2.0
pressure_field = clamp(body_pressure * 0.60 + close_location * 0.40, -1.0, 1.0)

distance_field = clamp(distance / 1.20, -1.0, 1.0)
momentum_field = clamp(momentum / 0.35, -1.0, 1.0)
raw_regime = (
    distance_field * 0.22 + momentum_field * 0.19 + slope_field * 0.14
    + slow_slope_field * 0.10 + rsi_field * 0.08 + efficiency_field * 0.09
    + pressure_field * 0.05 + structure_field * 0.05 + st_field * 0.20
)
regime = ema(raw_regime, 3)
chop_penalty = chop * 0.085
vol_penalty = clamp(vol_deviation * 0.04, 0.0, 0.06)
dynamic_gate = 0.22 + sensitivity * 0.12 + chop_penalty + vol_penalty
bull_price_ok = close_v > basis + safe_atr * sensitivity * 0.30
bear_price_ok = close_v < basis - safe_atr * sensitivity * 0.30

# Require confirmed SuperTrend votes to persist through the current bar.
st_confirm_bull = np.zeros(n, dtype=int)
st_confirm_bear = np.zeros(n, dtype=int)
for i in range(1, n):
    st_confirm_bull[i] = min(st_confirm_bull[i - 1] + 1, 4) if bull_st_confirmed[i] else 0
    st_confirm_bear[i] = min(st_confirm_bear[i - 1] + 1, 4) if bear_st_confirmed[i] else 0
st_required = np.where(chop > 0.72, 2, 1)
bull_st_persistent = st_confirm_bull >= st_required
bear_st_persistent = st_confirm_bear >= st_required
bull_candidate = (regime > dynamic_gate) & bull_price_ok & (momentum > 0.025) & bull_st_persistent
bear_candidate = (regime < -dynamic_gate) & bear_price_ok & (momentum < -0.025) & bear_st_persistent

required_bars = np.where(chop > 0.72, 3, np.where(chop > 0.40, 2, 1))
bull_confirm = np.zeros(n, dtype=int)
bear_confirm = np.zeros(n, dtype=int)
for i in range(1, n):
    bull_confirm[i] = min(bull_confirm[i - 1] + 1, 4) if bull_candidate[i] else 0
    bear_confirm[i] = min(bear_confirm[i - 1] + 1, 4) if bear_candidate[i] else 0
strong_bull = bull_candidate & full_bull_st & (regime > dynamic_gate + 0.26) & (momentum > 0.16) & (efficiency > 0.42)
strong_bear = bear_candidate & full_bear_st & (regime < -(dynamic_gate + 0.26)) & (momentum < -0.16) & (efficiency > 0.42)
bull_ready = ((bull_confirm >= required_bars) | strong_bull) & fast_bull & (mid_bull | slow_bull)
bear_ready = ((bear_confirm >= required_bars) | strong_bear) & fast_bear & (mid_bear | slow_bear)

trend = np.zeros(n, dtype=int)
last_flip = -1
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
for i in range(1, n):
    trend[i] = trend[i - 1]
    cooldown = 6 + int(round(chop[i] * 4.0))
    cooldown_done = last_flip < 0 or i - last_flip >= cooldown
    if trend[i] != 1 and bull_ready[i] and (cooldown_done or strong_bull[i]):
        trend[i] = 1
        long_signal[i] = True
        last_flip = i
    elif trend[i] != -1 and bear_ready[i] and (cooldown_done or strong_bear[i]):
        trend[i] = -1
        short_signal[i] = True

smooth_basis = ema(basis, smoothness) if smoothness > 1 else basis
smooth_atr = ema(safe_atr, smoothness) if smoothness > 1 else safe_atr
bullish = trend == 1
bearish = trend == -1
inner_distance = 0.55 * trail_size
outer_distance = 1.15 * trail_size
depth_distance = 1.60 * trail_size
inner_trail = np.where(bullish, smooth_basis - smooth_atr * inner_distance, np.where(bearish, smooth_basis + smooth_atr * inner_distance, smooth_basis))
outer_trail = np.where(bullish, smooth_basis - smooth_atr * outer_distance, np.where(bearish, smooth_basis + smooth_atr * outer_distance, smooth_basis))
depth_trail = np.where(bullish, smooth_basis - smooth_atr * depth_distance, np.where(bearish, smooth_basis + smooth_atr * depth_distance, smooth_basis))


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

plots = [
    {"name": "Trend Baseline", "data": plot_list(basis), "color": "#78909C", "overlay": True},
    {"name": "Trend Regime", "data": plot_list(regime), "color": "#42A5F5", "overlay": False},
    {"name": "Trend Direction", "data": [float(v) for v in trend], "color": "#AB47BC", "overlay": False},
]
if overlay_mode == "trail":
    plots.extend([
        {"name": "Inner Trail", "data": plot_list(inner_trail), "color": "#26A69A", "overlay": True},
        {"name": "Outer Trail", "data": plot_list(outer_trail), "color": "#FFA726", "overlay": True},
        {"name": "Depth Trail", "data": plot_list(depth_trail), "color": "#EF5350", "overlay": True},
    ])
elif overlay_mode == "bands":
    for label, distance_value, color in [
        ("Inner", inner_distance, "#26A69A"), ("Outer", outer_distance, "#FFA726"), ("Depth", depth_distance, "#EF5350")
    ]:
        plots.append({"name": label + " Upper Band", "data": plot_list(smooth_basis + smooth_atr * distance_value), "color": color, "overlay": True})
        plots.append({"name": label + " Lower Band", "data": plot_list(smooth_basis - smooth_atr * distance_value), "color": color, "overlay": True})

output = {
    "name": my_indicator_name,
    "plots": plots,
    "signals": [
        {"type": "buy", "text": "ATT+", "data": [float(low_v[i]) * 0.995 if long_signal[i] and np.isfinite(low_v[i]) else None for i in range(n)], "color": "#00E676"},
        {"type": "sell", "text": "ATT-", "data": [float(high_v[i]) * 1.005 if short_signal[i] and np.isfinite(high_v[i]) else None for i in range(n)], "color": "#FF5252"},
    ],
    "layers": [],
}
