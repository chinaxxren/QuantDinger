"""Reviewed backend calculation for the cmo indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, np, pd


def _cmo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    delta = _close(df).diff()
    up = delta.clip(lower=0).rolling(period, min_periods=period).sum()
    down = (-delta.clip(upper=0)).rolling(period, min_periods=period).sum()
    values = 100 * (up - down) / (up + down).replace(0, np.nan)
    return _output("Chande Momentum Oscillator", [_line("cmo", f"CMO({period})", values)])


compute = _cmo
