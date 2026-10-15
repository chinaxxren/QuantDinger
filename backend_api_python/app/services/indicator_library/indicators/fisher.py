"""Reviewed backend calculation for the fisher indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _fisher(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=200)
    signal_period = _integer(params, "signal_period", 1, minimum=1, maximum=50)
    price = (_series(df, "high") + _series(df, "low")) / 2
    rolling_high = price.rolling(period, min_periods=period).max().to_numpy()
    rolling_low = price.rolling(period, min_periods=period).min().to_numpy()
    source = price.to_numpy()
    fisher = np.full(len(df), np.nan)
    previous_value = 0.0
    previous_fisher = 0.0
    for index in range(len(df)):
        if (
            not np.isfinite(rolling_high[index])
            or not np.isfinite(rolling_low[index])
            or not np.isfinite(source[index])
        ):
            continue
        width = rolling_high[index] - rolling_low[index]
        raw = 0.0 if width <= 0 else 2 * ((source[index] - rolling_low[index]) / width - 0.5)
        value = float(np.clip(0.33 * raw + 0.67 * previous_value, -0.999, 0.999))
        current = 0.5 * np.log((1 + value) / (1 - value)) + 0.5 * previous_fisher
        fisher[index] = current
        previous_value, previous_fisher = value, current
    fisher_series = pd.Series(fisher, index=df.index)
    signal = fisher_series.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output(
        "Fisher Transform",
        [
            _line("fisher", "Fisher", fisher_series, color="#2962ff"),
            _line("fisher_signal", "Signal", signal, color="#ff6d00"),
        ],
    )


compute = _fisher
