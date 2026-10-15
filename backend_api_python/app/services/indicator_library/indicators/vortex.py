"""Reviewed backend calculation for the vortex indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _vortex(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    positive = (high - low.shift(1)).abs().rolling(period, min_periods=period).sum()
    negative = (low - high.shift(1)).abs().rolling(period, min_periods=period).sum()
    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(
        axis=1
    )
    range_sum = true_range.rolling(period, min_periods=period).sum().replace(0, np.nan)
    return _output(
        "Vortex Indicator",
        [
            _line("vortex_positive", "VI+", positive / range_sum, color="#26a69a"),
            _line("vortex_negative", "VI-", negative / range_sum, color="#ef5350"),
        ],
    )


compute = _vortex
