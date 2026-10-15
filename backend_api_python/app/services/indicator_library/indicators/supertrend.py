"""Reviewed backend calculation for the supertrend indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _atr, _clean, _integer, _line, _number, _series, np, pd


def _supertrend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2)
    multiplier = _number(params, "multiplier", 3.0, minimum=0.1, maximum=10)
    atr = _atr(df, period)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    hl2 = (high + low) / 2
    upper, lower = hl2 + multiplier * atr, hl2 - multiplier * atr
    final_upper = pd.Series(np.nan, index=df.index)
    final_lower = pd.Series(np.nan, index=df.index)
    line = pd.Series(np.nan, index=df.index)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if index < period - 1 or not np.isfinite(upper.iloc[index]) or not np.isfinite(lower.iloc[index]):
            continue
        if index == period - 1 or direction[index - 1] == 0:
            final_upper.iloc[index], final_lower.iloc[index] = upper.iloc[index], lower.iloc[index]
            direction[index] = 1 if close.iloc[index] >= hl2.iloc[index] else -1
        else:
            final_upper.iloc[index] = (
                upper.iloc[index]
                if upper.iloc[index] < final_upper.iloc[index - 1]
                or close.iloc[index - 1] > final_upper.iloc[index - 1]
                else final_upper.iloc[index - 1]
            )
            final_lower.iloc[index] = (
                lower.iloc[index]
                if lower.iloc[index] > final_lower.iloc[index - 1]
                or close.iloc[index - 1] < final_lower.iloc[index - 1]
                else final_lower.iloc[index - 1]
            )
            direction[index] = (
                1
                if close.iloc[index] > final_upper.iloc[index - 1]
                else -1
                if close.iloc[index] < final_lower.iloc[index - 1]
                else direction[index - 1]
            )
        line.iloc[index] = final_lower.iloc[index] if direction[index] == 1 else final_upper.iloc[index]
    previous = np.concatenate(([0], direction[:-1]))
    buy = np.where((direction == 1) & (previous == -1), low * 0.995, np.nan)
    sell = np.where((direction == -1) & (previous == 1), high * 1.005, np.nan)
    return {
        "name": "SuperTrend",
        "plots": [
            _line(
                "supertrend_up", "SuperTrend Up", np.where(direction == 1, line, np.nan), overlay=True, color="#00E676"
            ),
            _line(
                "supertrend_down",
                "SuperTrend Down",
                np.where(direction == -1, line, np.nan),
                overlay=True,
                color="#FF5252",
            ),
        ],
        "signals": [
            {"type": "buy", "text": "L", "data": _clean(buy), "color": "#00E676"},
            {"type": "sell", "text": "S", "data": _clean(sell), "color": "#FF5252"},
        ],
        "layers": [],
    }


compute = _supertrend
