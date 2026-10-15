"""Reviewed backend calculation for the dpo indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, pd


def _dpo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    offset = period // 2 + 1
    average = _close(df).rolling(period, min_periods=period).mean().shift(offset)
    return _output(
        "Detrended Price Oscillator", [_line("dpo", f"DPO({period})", _close(df) - average, color="#2962ff")]
    )


compute = _dpo
