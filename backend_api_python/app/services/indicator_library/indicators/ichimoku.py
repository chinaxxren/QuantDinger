"""Reviewed backend calculation for the ichimoku indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, pd


def _ichimoku(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    conversion_period = _integer(params, "conversion_period", 9, minimum=2, maximum=100)
    base_period = _integer(params, "base_period", 26, minimum=2, maximum=200)
    span_b_period = _integer(params, "span_b_period", 52, minimum=2, maximum=300)
    high, low = _series(df, "high"), _series(df, "low")

    def midpoint(period: int) -> pd.Series:
        return (high.rolling(period, min_periods=period).max() + low.rolling(period, min_periods=period).min()) / 2

    conversion = midpoint(conversion_period)
    base = midpoint(base_period)
    span_a = (conversion + base) / 2
    span_b = midpoint(span_b_period)
    return _output(
        "Ichimoku Cloud",
        [
            _line("ichimoku_conversion", "Tenkan-sen", conversion, overlay=True, color="#26a69a"),
            _line("ichimoku_base", "Kijun-sen", base, overlay=True, color="#ef5350"),
            _line("ichimoku_span_a", "Senkou Span A", span_a, overlay=True, color="#66bb6a"),
            _line("ichimoku_span_b", "Senkou Span B", span_b, overlay=True, color="#ab47bc"),
        ],
    )


compute = _ichimoku
