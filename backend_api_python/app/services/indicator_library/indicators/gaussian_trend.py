"""Reviewed backend calculation for the gaussian_trend indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _atr,
    _close,
    _integer,
    _line,
    _number,
    _output,
    _series,
    np,
    pd,
)


def _gaussian_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    poles = _integer(params, "poles", 3, minimum=1, maximum=6)
    atr_period = _integer(params, "atr_period", 14, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 1.5, minimum=0.25, maximum=8)
    center = _close(df)
    for _ in range(poles):
        center = center.ewm(span=period, adjust=False, min_periods=period).mean()
    atr = _atr(df, atr_period)
    close = _close(df).to_numpy()
    center_values, atr_values = center.to_numpy(), atr.to_numpy()
    trend = np.zeros(len(df), dtype=int)
    trend_line = np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(center_values[index]) or not np.isfinite(atr_values[index]):
            continue
        upper = center_values[index] + multiplier * atr_values[index]
        lower = center_values[index] - multiplier * atr_values[index]
        if index == 0 or trend[index - 1] == 0:
            trend[index] = 1 if close[index] >= center_values[index] else -1
        elif trend[index - 1] > 0:
            trend[index] = -1 if close[index] < lower else 1
        else:
            trend[index] = 1 if close[index] > upper else -1
        trend_line[index] = lower if trend[index] > 0 else upper
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    low, high = _series(df, "low"), _series(df, "high")
    return {
        **_output(
            "Gaussian Filter Trend",
            [
                _line("gaussian_filter", "Gaussian Filter", center, overlay=True, color="#2962ff"),
                _line("gaussian_trend", "Gaussian Trend", trend_line, overlay=True, color="#ffb300"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "GF+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "GF-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


compute = _gaussian_trend
