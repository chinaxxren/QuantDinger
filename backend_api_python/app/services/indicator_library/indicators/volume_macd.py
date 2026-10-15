"""Reviewed backend calculation for the volume_macd indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _bar,
    _close,
    _ema,
    _integer,
    _line,
    _output,
    _series,
    np,
    pd,
)


def _volume_macd(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_length", 12, minimum=2, maximum=100)
    slow = _integer(params, "slow_length", 26, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_length", 9, minimum=2, maximum=100)
    show_histogram = bool(params.get("histogram", True))
    if fast >= slow:
        raise ValueError("invalid parameter: fast_length")
    close = _close(df)
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    volume_sum = volume.rolling(slow, min_periods=1).sum()
    weighted_price = ((close * volume).rolling(slow, min_periods=1).sum() / volume_sum.replace(0, np.nan)).fillna(close)
    macd = _ema(weighted_price, fast) - _ema(weighted_price, slow)
    signal = _ema(macd, signal_period)
    plots = [
        _line("volume_macd", "VW MACD", macd, color="#26a69a"),
        _line("volume_macd_signal", "Signal", signal, color="#ffb300"),
    ]
    plots.append(
        _bar(
            "volume_macd_histogram",
            "Histogram",
            macd - signal if show_histogram else np.full(len(df), np.nan),
            color="#90caf9",
        )
    )
    macd_values, signal_values = macd.to_numpy(), signal.to_numpy()
    previous_macd = np.concatenate(([np.nan], macd_values[:-1]))
    previous_signal = np.concatenate(([np.nan], signal_values[:-1]))
    finite = (
        np.isfinite(macd_values)
        & np.isfinite(signal_values)
        & np.isfinite(previous_macd)
        & np.isfinite(previous_signal)
    )
    buy = finite & (previous_macd <= previous_signal) & (macd_values > signal_values)
    sell = finite & (previous_macd >= previous_signal) & (macd_values < signal_values)
    return {
        **_output("Volume Weighted MACD", plots),
        "signals": [
            {
                "type": "buy",
                "text": "VW MACD+",
                "data": [float(value) if flag else None for value, flag in zip(macd_values, buy)],
                "color": "#00c853",
            },
            {
                "type": "sell",
                "text": "VW MACD-",
                "data": [float(value) if flag else None for value, flag in zip(macd_values, sell)],
                "color": "#ff1744",
            },
        ],
    }


compute = _volume_macd
