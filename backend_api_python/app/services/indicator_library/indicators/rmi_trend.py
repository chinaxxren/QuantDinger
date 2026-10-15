"""Reviewed backend calculation for the rmi_trend indicator."""

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
    _wilder,
    np,
    pd,
)


def _rmi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14, minimum=2, maximum=100)
    positive_threshold = _number(params, "pmom", 66, minimum=50, maximum=100)
    negative_threshold = _number(params, "nmom", 30, minimum=0, maximum=50)
    close = _close(df)
    delta = close.diff()
    gain = _wilder(delta.clip(lower=0).fillna(0), period)
    loss = _wilder((-delta.clip(upper=0)).fillna(0), period)
    rsi = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)
    typical = (_series(df, "high") + _series(df, "low") + close) / 3
    flow = typical * _series(df, "volume").fillna(0)
    direction = typical.diff()
    positive = flow.where(direction > 0, 0).rolling(period, min_periods=period).sum()
    negative = flow.where(direction < 0, 0).rolling(period, min_periods=period).sum()
    mfi = (100 - 100 / (1 + positive / negative.replace(0, np.nan))).fillna(50)
    rmi = ((rsi + mfi) / 2).to_numpy(dtype=float)
    close_values = close.to_numpy(dtype=float)
    ema5 = close.ewm(span=5, adjust=False, min_periods=5).mean().to_numpy(dtype=float)
    ema_change = np.full(len(df), np.nan)
    if len(df) > 1:
        ema_change[1:] = ema5[1:] - ema5[:-1]
    positive = np.zeros(len(df), dtype=bool)
    negative = np.zeros(len(df), dtype=bool)
    long_signal = np.zeros(len(df), dtype=bool)
    short_signal = np.zeros(len(df), dtype=bool)
    for index in range(len(df)):
        prev = rmi[index - 1] if index else np.nan
        if (
            np.isfinite(prev)
            and np.isfinite(rmi[index])
            and np.isfinite(ema_change[index])
            and prev < positive_threshold
            and rmi[index] > positive_threshold
            and rmi[index] > negative_threshold
            and ema_change[index] > 0
        ):
            positive[index], long_signal[index] = True, True
        elif (
            np.isfinite(rmi[index])
            and np.isfinite(ema_change[index])
            and rmi[index] < negative_threshold
            and ema_change[index] < 0
        ):
            negative[index], short_signal[index] = True, True
        elif index:
            positive[index], negative[index] = positive[index - 1], negative[index - 1]
    high, low = _series(df, "high"), _series(df, "low")
    atr = _atr(df, 30)
    band_source = pd.concat([atr * 0.3, close * 0.003], axis=1).min(axis=1).shift(20) * 4
    price_range = (high - low).clip(lower=0)
    range_sum = price_range.rolling(20, min_periods=20).sum()
    weighted_sum = (close * price_range).rolling(20, min_periods=20).sum()
    rwma = weighted_sum / range_sum.replace(0, np.nan)
    rwma_up = rwma - band_source
    rwma_down = rwma + band_source
    plots = [
        _line("rmi_up", "RMI Trend Up", rwma_up.where(positive), overlay=True, color="#00bcd4"),
        _line("rmi_down", "RMI Trend Down", rwma_down.where(negative), overlay=True, color="#ff5252"),
        _line("rmi_up_upper", "Upper Up Band", (rwma_up + band_source).where(positive), overlay=True, color="#80deea"),
        _line("rmi_up_lower", "Lower Up Band", (rwma_up - band_source).where(positive), overlay=True, color="#80deea"),
        _line(
            "rmi_down_upper",
            "Upper Down Band",
            (rwma_down + band_source).where(negative),
            overlay=True,
            color="#ef9a9a",
        ),
        _line(
            "rmi_down_lower",
            "Lower Down Band",
            (rwma_down - band_source).where(negative),
            overlay=True,
            color="#ef9a9a",
        ),
    ]
    buys = [
        float(low.iloc[index]) * 0.995 if long_signal[index] and np.isfinite(low.iloc[index]) else None
        for index in range(len(df))
    ]
    sells = [
        float(high.iloc[index]) * 1.005 if short_signal[index] and np.isfinite(high.iloc[index]) else None
        for index in range(len(df))
    ]
    return {
        **_output("RMI Trend Sniper", plots),
        "signals": [
            {"type": "buy", "text": "RMI+", "data": buys, "color": "#00e676"},
            {"type": "sell", "text": "RMI-", "data": sells, "color": "#ff5252"},
        ],
    }


compute = _rmi
