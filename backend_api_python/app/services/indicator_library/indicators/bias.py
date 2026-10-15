"""Reviewed backend calculation for the bias indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, pd


def _bias(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    close = _close(df)
    plots = []
    for key, default_period in (("short", 6), ("medium", 12), ("long", 24)):
        period = _integer(params, key, default_period)
        plots.append(
            _line(key, f"BIAS {key}({period})", (close / close.rolling(period, min_periods=period).mean() - 1) * 100)
        )
    return _output("Bias Ratio", plots)


compute = _bias
