"""Reviewed backend calculation for the zero_lag_trend indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _atr,
    _ema,
    _integer,
    _line,
    _number,
    _output,
    _series,
    np,
    pd,
)


def _zero_lag_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 70, minimum=2, maximum=300)
    multiplier = _number(params, "mult", 1.2, minimum=0.1, maximum=10)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    lag = max(1, (period - 1) // 2)
    zlema = _ema(close + (close - close.shift(lag)), period).to_numpy()
    atr = _atr(df, period)
    volatility = atr.rolling(period * 3, min_periods=period * 3).max().mul(multiplier).to_numpy()
    closes = close.to_numpy()
    upper, lower = zlema + volatility, zlema - volatility
    trend = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if (
            not np.isfinite(zlema[index])
            or not np.isfinite(upper[index])
            or not np.isfinite(lower[index])
            or not np.isfinite(closes[index])
        ):
            continue
        if index == 0 or trend[index - 1] == 0:
            trend[index] = 1 if closes[index] >= zlema[index] else -1
        elif (
            index
            and np.isfinite(upper[index - 1])
            and closes[index - 1] <= upper[index - 1]
            and closes[index] > upper[index - 1]
        ):
            trend[index] = 1
        elif (
            index
            and np.isfinite(lower[index - 1])
            and closes[index - 1] >= lower[index - 1]
            and closes[index] < lower[index - 1]
        ):
            trend[index] = -1
        else:
            trend[index] = trend[index - 1]
    bull = np.where(trend == 1, zlema, np.nan)
    bear = np.where(trend == -1, zlema, np.nan)
    upper_plot = np.where(trend == -1, upper, np.nan)
    lower_plot = np.where(trend == 1, lower, np.nan)
    previous = np.concatenate(([0], trend[:-1]))
    bull_flip, bear_flip = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    buys, sells = np.zeros(len(df), dtype=bool), np.zeros(len(df), dtype=bool)
    for index in range(1, len(df)):
        if trend[index] == trend[index - 1] == 1 and np.isfinite(zlema[index]) and np.isfinite(zlema[index - 1]):
            buys[index] = closes[index - 1] <= zlema[index - 1] and closes[index] > zlema[index]
        elif trend[index] == trend[index - 1] == -1 and np.isfinite(zlema[index]) and np.isfinite(zlema[index - 1]):
            sells[index] = closes[index - 1] >= zlema[index - 1] and closes[index] < zlema[index]
    lows, highs = low.to_numpy(), high.to_numpy()
    return {
        **_output(
            "Zero Lag Trend Signals",
            [
                _line("zero_lag_bull", "Zero Lag Bull", bull, overlay=True, color="#00ffbb"),
                _line("zero_lag_bear", "Zero Lag Bear", bear, overlay=True, color="#ff1100"),
                _line("zero_lag_upper", "Upper Band", upper_plot, overlay=True, color="#ff5252"),
                _line("zero_lag_lower", "Lower Band", lower_plot, overlay=True, color="#00e676"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "Long",
                "data": [float(lows[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "Short",
                "data": [float(highs[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
            {
                "type": "sell",
                "text": "Bear",
                "data": [float(highs[index]) * 1.015 if bear_flip[index] else None for index in range(len(df))],
                "color": "#ff1744",
            },
            {
                "type": "buy",
                "text": "Bull",
                "data": [float(lows[index]) * 0.985 if bull_flip[index] else None for index in range(len(df))],
                "color": "#00c853",
            },
        ],
    }


compute = _zero_lag_trend
