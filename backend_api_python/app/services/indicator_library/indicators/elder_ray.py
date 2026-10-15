"""Reviewed backend calculation for the elder_ray indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, _series, pd


def _elder_ray(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 13, minimum=2, maximum=200)
    baseline = _ema(_close(df), period)
    return _output(
        "Elder Ray Index",
        [
            _line("bull_power", "Bull Power", _series(df, "high") - baseline, color="#26a69a"),
            _line("bear_power", "Bear Power", _series(df, "low") - baseline, color="#ef5350"),
        ],
    )


compute = _elder_ray
