"""Reviewed backend calculation for the trend_state indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _integer,
    _line,
    _number,
    _output,
    _series,
    _wilder,
    np,
    pd,
)


def _trend_state(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20, minimum=2, maximum=200)
    multiplier = _number(params, "multiplier", 3.5, minimum=0.1, maximum=10)
    source_name = str(params.get("src_type", "close")).lower()
    open_price, high, low, close = (_series(df, key).to_numpy() for key in ("open", "high", "low", "close"))
    source = {
        "hl2": (high + low) / 2,
        "hlc3": (high + low + close) / 3,
        "ohlc4": (open_price + high + low + close) / 4,
    }.get(source_name, close)
    movement = np.full(len(df), np.nan)
    if len(df) > 1:
        movement[1:] = np.abs(np.diff(source))
    movement_rma = _wilder(pd.Series(movement, index=df.index), period).to_numpy()
    adaptive_range = movement_rma * multiplier
    filter_line = np.full(len(df), np.nan)
    trend = np.zeros(len(df), dtype=int)
    for index in range(period, len(df)):
        if not np.isfinite(source[index]) or not np.isfinite(adaptive_range[index]):
            if index > period:
                filter_line[index], trend[index] = filter_line[index - 1], trend[index - 1]
            continue
        if index == period or not np.isfinite(filter_line[index - 1]):
            filter_line[index] = source[index]
            continue
        previous = filter_line[index - 1]
        if source[index] > previous + adaptive_range[index]:
            filter_line[index] = source[index] - adaptive_range[index]
        elif source[index] < previous - adaptive_range[index]:
            filter_line[index] = source[index] + adaptive_range[index]
        else:
            filter_line[index] = previous
        trend[index] = 1 if filter_line[index] > previous else -1 if filter_line[index] < previous else trend[index - 1]
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    low, high = _series(df, "low"), _series(df, "high")
    return {
        **_output(
            "Trend State Signals",
            [_line("trend_state_filter", "Step Filter", filter_line, overlay=True, color="#26a69a")],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "TSS+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "TSS-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


compute = _trend_state
