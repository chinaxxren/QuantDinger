"""Reviewed backend calculation for the rvi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _rvi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=100)
    movement = _series(df, "close") - _series(df, "open")
    bar_range = (_series(df, "high") - _series(df, "low")).clip(lower=0)
    weights = np.array([1.0, 2.0, 2.0, 1.0])
    weighted_move = movement.rolling(4, min_periods=4).apply(
        lambda values: float(np.dot(values, weights) / 6), raw=True
    )
    weighted_range = bar_range.rolling(4, min_periods=4).apply(
        lambda values: float(np.dot(values, weights) / 6), raw=True
    )
    vigor = weighted_move / weighted_range.replace(0, np.nan)
    signal = vigor.rolling(period, min_periods=period).mean()
    return _output(
        "Relative Vigor Index",
        [
            _line("rvi", "RVI", vigor, color="#2962ff"),
            _line("rvi_signal", "Signal", signal, color="#ff6d00"),
        ],
    )


compute = _rvi
