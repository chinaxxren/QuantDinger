"""Reviewed backend calculation for the keltner indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _atr,
    _close,
    _ema,
    _integer,
    _line,
    _number,
    _output,
    pd,
)


def _keltner(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    atr_period = _integer(params, "atr_period", 10, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 2.0, minimum=0.25, maximum=8.0)
    center = _ema(_close(df), period)
    atr = _atr(df, atr_period)
    return _output(
        "Keltner Channel",
        [
            _line("keltner_upper", "Keltner Upper", center + multiplier * atr, overlay=True, color="#26a69a"),
            _line("keltner_center", f"EMA({period})", center, overlay=True, color="#2962ff"),
            _line("keltner_lower", "Keltner Lower", center - multiplier * atr, overlay=True, color="#ef5350"),
        ],
    )


compute = _keltner
