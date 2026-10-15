"""Reviewed backend calculation for the pmax indicator."""

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


def _pmax(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    ma_period = _integer(params, "ma_period", 10, minimum=5, maximum=60)
    atr_period = _integer(params, "atr_period", 10, minimum=5, maximum=60)
    multiplier = _number(params, "atr_multiplier", 3, minimum=1, maximum=6)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    baseline, atr = _ema(close, ma_period), _atr(df, atr_period)
    long_basic, short_basic = baseline - multiplier * atr, baseline + multiplier * atr
    long_stop, short_stop, pmax = np.full(len(df), np.nan), np.full(len(df), np.nan), np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(long_basic.iloc[index]) or not np.isfinite(short_basic.iloc[index]):
            continue
        if (
            index == 0
            or direction[index - 1] == 0
            or not np.isfinite(long_stop[index - 1])
            or not np.isfinite(short_stop[index - 1])
        ):
            long_stop[index], short_stop[index] = long_basic.iloc[index], short_basic.iloc[index]
            direction[index] = 1 if close.iloc[index] >= baseline.iloc[index] else -1
        else:
            long_stop[index] = (
                max(long_basic.iloc[index], long_stop[index - 1])
                if baseline.iloc[index - 1] > long_stop[index - 1]
                else long_basic.iloc[index]
            )
            short_stop[index] = (
                min(short_basic.iloc[index], short_stop[index - 1])
                if baseline.iloc[index - 1] < short_stop[index - 1]
                else short_basic.iloc[index]
            )
            direction[index] = (
                1
                if direction[index - 1] == -1 and baseline.iloc[index] > short_stop[index - 1]
                else -1
                if direction[index - 1] == 1 and baseline.iloc[index] < long_stop[index - 1]
                else direction[index - 1]
            )
        pmax[index] = long_stop[index] if direction[index] == 1 else short_stop[index]
    previous = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction == 1) & (previous == -1), (direction == -1) & (previous == 1)
    return {
        **_output(
            "PMax Trend Filter",
            [
                _line("pmax_baseline", "EMA Baseline", baseline, overlay=True, color="#ffb300"),
                _line("pmax_up", "PMax Up", np.where(direction == 1, pmax, np.nan), overlay=True, color="#00e676"),
                _line("pmax_down", "PMax Down", np.where(direction == -1, pmax, np.nan), overlay=True, color="#ff5252"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "PMax+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "PMax-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


compute = _pmax
