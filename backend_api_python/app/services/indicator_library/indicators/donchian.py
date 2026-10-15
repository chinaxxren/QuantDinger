"""Reviewed backend calculation for the donchian indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _donchian(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    upper = high.rolling(period, min_periods=period).max().shift(1)
    lower = low.rolling(period, min_periods=period).min().shift(1)
    middle = (upper + lower) / 2
    above = (close > upper).fillna(False).to_numpy()
    below = (close < lower).fillna(False).to_numpy()
    previous_above = np.concatenate([[False], above[:-1]])
    previous_below = np.concatenate([[False], below[:-1]])
    buy = [float(low.iloc[index]) if above[index] and not previous_above[index] else None for index in range(len(df))]
    sell = [float(high.iloc[index]) if below[index] and not previous_below[index] else None for index in range(len(df))]
    return {
        **_output(
            "Donchian Channel",
            [
                _line("donchian_upper", "Donchian Upper", upper, overlay=True, color="#26a69a"),
                _line("donchian_middle", "Donchian Middle", middle, overlay=True, color="#90a4ae"),
                _line("donchian_lower", "Donchian Lower", lower, overlay=True, color="#ef5350"),
            ],
        ),
        "signals": [
            {"type": "buy", "text": "DC+", "data": buy, "color": "#00e676"},
            {"type": "sell", "text": "DC-", "data": sell, "color": "#ff5252"},
        ],
    }


compute = _donchian
