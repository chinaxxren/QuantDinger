"""Reviewed backend calculation for the obv indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _line, _output, _series, np, pd


def _obv(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    close, volume = _close(df), _series(df, "volume").fillna(0)
    direction = np.sign(close.diff()).fillna(0)
    values = (direction * volume).cumsum()
    if len(values):
        values.iloc[0] = volume.iloc[0]
    return _output("OBV", [_line("obv", "OBV", values)])


compute = _obv
