"""Reviewed backend calculation for the aroon indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _aroon(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 25, minimum=2, maximum=200)
    high, low = _series(df, "high"), _series(df, "low")

    def most_recent_age(values: np.ndarray, find_max: bool) -> float:
        if not np.isfinite(values).all():
            return np.nan
        extreme = np.max(values) if find_max else np.min(values)
        positions = np.flatnonzero(values == extreme)
        return float(len(values) - 1 - positions[-1])

    high_age = high.rolling(period, min_periods=period).apply(lambda values: most_recent_age(values, True), raw=True)
    low_age = low.rolling(period, min_periods=period).apply(lambda values: most_recent_age(values, False), raw=True)
    up = 100 * (period - high_age) / period
    down = 100 * (period - low_age) / period
    return _output(
        "Aroon Oscillator",
        [
            _line("aroon_up", "Aroon Up", up, color="#26a69a"),
            _line("aroon_down", "Aroon Down", down, color="#ef5350"),
            _line("aroon", "Aroon Oscillator", up - down, color="#2962ff"),
        ],
    )


compute = _aroon
