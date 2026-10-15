"""Reviewed backend calculation for the vidya indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, np, pd


def _vidya(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    momentum_period = _integer(params, "momentum_period", 9, minimum=2, maximum=100)
    signal_period = _integer(params, "signal_period", 9, minimum=2, maximum=100)
    close = _close(df)
    change = close.diff()
    up = change.clip(lower=0).rolling(momentum_period, min_periods=momentum_period).sum()
    down = (-change.clip(upper=0)).rolling(momentum_period, min_periods=momentum_period).sum()
    ratio = ((up - down).abs() / (up + down).replace(0, np.nan)).fillna(0).to_numpy()
    values = np.full(len(df), np.nan)
    close_values = close.to_numpy()
    alpha = 2 / (period + 1)
    for index, value in enumerate(close_values):
        if not np.isfinite(value):
            continue
        current_alpha = alpha * min(1, max(0, ratio[index]))
        values[index] = (
            value
            if index == 0 or not np.isfinite(values[index - 1])
            else current_alpha * value + (1 - current_alpha) * values[index - 1]
        )
    vidya = pd.Series(values, index=df.index)
    return _output(
        "Variable Moving Average",
        [
            _line("vidya", "VIDYA", vidya, overlay=True, color="#2962ff"),
            _line("vidya_signal", "VIDYA Signal", _ema(vidya, signal_period), overlay=True, color="#ff6d00"),
        ],
    )


compute = _vidya
