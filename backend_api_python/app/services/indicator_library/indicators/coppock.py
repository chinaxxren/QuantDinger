"""Reviewed backend calculation for the coppock indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, np, pd


def _coppock(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    long = _integer(params, "long_roc", 14, minimum=2, maximum=200)
    short = _integer(params, "short_roc", 11, minimum=2, maximum=200)
    wma_period = _integer(params, "wma_period", 10, minimum=2, maximum=100)
    if long == short:
        raise ValueError("invalid parameter: roc periods")
    close = _close(df)
    roc = 100 * ((close / close.shift(long) - 1) + (close / close.shift(short) - 1))
    weights = np.arange(1, wma_period + 1, dtype=float)
    values = roc.rolling(wma_period, min_periods=wma_period).apply(
        lambda window: float(np.dot(window, weights) / weights.sum()), raw=True
    )
    return _output("Coppock Curve", [_line("coppock", "Coppock Curve", values, color="#2962ff")])


compute = _coppock
