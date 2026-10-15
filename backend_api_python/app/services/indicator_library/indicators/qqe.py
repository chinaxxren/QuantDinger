"""Reviewed backend calculation for the qqe indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _close,
    _ema,
    _integer,
    _line,
    _number,
    _output,
    _wilder,
    np,
    pd,
)


def _qqe(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    rsi_period = _integer(params, "rsi_period", 14, minimum=2, maximum=100)
    rsi_smoothing = _integer(params, "rsi_smoothing", 5, minimum=1, maximum=50)
    factor = _number(params, "qqe_factor", 4.236, minimum=0.5, maximum=10)
    delta = _close(df).diff()
    gain = _wilder(delta.clip(lower=0).fillna(0), rsi_period)
    loss = _wilder((-delta.clip(upper=0)).fillna(0), rsi_period)
    rsi = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50).clip(0, 100)
    smoothed = _ema(rsi, rsi_smoothing)
    volatility = _ema(smoothed.diff().abs(), rsi_period)
    distance = factor * _ema(volatility, rsi_period)
    long_band = pd.Series(np.nan, index=df.index)
    short_band = pd.Series(np.nan, index=df.index)
    trend = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        value, width = smoothed.iloc[index], distance.iloc[index]
        if not np.isfinite(value) or not np.isfinite(width):
            continue
        lower, upper = value - width, value + width
        if index == 0 or not np.isfinite(long_band.iloc[index - 1]):
            long_band.iloc[index], short_band.iloc[index], trend[index] = lower, upper, 1
            continue
        long_band.iloc[index] = (
            max(long_band.iloc[index - 1], lower)
            if smoothed.iloc[index - 1] > long_band.iloc[index - 1] and value > long_band.iloc[index - 1]
            else lower
        )
        short_band.iloc[index] = (
            min(short_band.iloc[index - 1], upper)
            if smoothed.iloc[index - 1] < short_band.iloc[index - 1] and value < short_band.iloc[index - 1]
            else upper
        )
        trend[index] = (
            1 if value > short_band.iloc[index - 1] else -1 if value < long_band.iloc[index - 1] else trend[index - 1]
        )
    trail = pd.Series(np.where(trend == 1, long_band, short_band), index=df.index)
    return _output(
        "QQE Signals",
        [
            _line("qqe_rsi", "QQE RSI", smoothed),
            _line("qqe_trail", "QQE Trail", trail, color="#ff6d00"),
        ],
    )


compute = _qqe
