"""Reviewed backend calculation for the cci indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, np, pd


def _cci(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    middle = typical.rolling(period, min_periods=period).mean()
    deviation = typical.rolling(period, min_periods=period).apply(
        lambda values: np.mean(np.abs(values - np.mean(values))), raw=True
    )
    return _output("CCI", [_line("cci", f"CCI({period})", (typical - middle) / (0.015 * deviation.replace(0, np.nan)))])


compute = _cci
