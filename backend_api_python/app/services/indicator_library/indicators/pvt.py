"""Reviewed backend calculation for the pvt indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, np, pd


def _pvt(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    signal_period = _integer(params, "signal_period", 21, minimum=1, maximum=200)
    close = _close(df)
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    returns = (close / close.shift(1).replace(0, np.nan) - 1).replace([np.inf, -np.inf], np.nan).fillna(0)
    pvt = (returns * volume).cumsum()
    signal = pvt.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output(
        "Price Volume Trend",
        [
            _line("pvt", "PVT", pvt, color="#2962ff"),
            _line("pvt_signal", "Signal", signal, color="#ff6d00"),
        ],
    )


compute = _pvt
