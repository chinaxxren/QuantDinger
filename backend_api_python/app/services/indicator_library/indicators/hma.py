"""Reviewed backend calculation for the hma indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _wma, np, pd


def _hma(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=300)
    half_period = max(1, period // 2)
    root_period = max(1, int(np.sqrt(period)))
    close = _close(df)
    raw = 2 * _wma(close, half_period) - _wma(close, period)
    values = _wma(raw, root_period)
    return _output("Hull Moving Average", [_line("hma", f"HMA({period})", values, overlay=True, color="#2962ff")])


compute = _hma
