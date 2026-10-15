"""Reviewed backend calculation for the vwap_channel indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _number, _output, _series, np, pd


def _vwap_channel(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 30, minimum=5, maximum=200)
    deviation = _number(params, "deviation", 1.5, minimum=0.25, maximum=5)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    typical = (high + low + close) / 3
    total = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    vwap = (typical * volume).rolling(period, min_periods=period).sum() / total
    variance = ((typical * typical * volume).rolling(period, min_periods=period).sum() / total - vwap * vwap).clip(
        lower=0
    )
    std = variance.pow(0.5)
    return _output(
        "VWAP Price Channel",
        [
            _line("vwap_channel", "VWAP", vwap, overlay=True, color="#2962ff"),
            _line("vwap_upper", "VWAP Upper", vwap + deviation * std, overlay=True, color="#ab47bc"),
            _line("vwap_lower", "VWAP Lower", vwap - deviation * std, overlay=True, color="#ab47bc"),
        ],
    )


compute = _vwap_channel
