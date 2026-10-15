"""Reviewed backend calculation for the super_bollinger indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _number, _output, _series, np, pd


def _super_bollinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "prd", 12, minimum=2, maximum=200)
    multiplier = _number(params, "mult", 2, minimum=0.1, maximum=10)
    show_zigzag = bool(params.get("show_zigzag", True))
    signal_mode = str(params.get("signal", "Signal")).lower()
    deviation_mode = str(params.get("dev", "ZigZag")).lower()
    show_tp = bool(params.get("show_tp", False))
    tp_type = str(params.get("tp_type", "Median")).lower()
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    basis = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper, lower = basis + multiplier * std, basis - multiplier * std
    closes = close.to_numpy()
    trend, sbt = np.zeros(len(df), dtype=int), np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(closes[index]) or not np.isfinite(upper.iloc[index]) or not np.isfinite(lower.iloc[index]):
            if index:
                trend[index], sbt[index] = trend[index - 1], sbt[index - 1]
            continue
        trend[index] = (
            1 if closes[index] > upper.iloc[index] else -1 if closes[index] < lower.iloc[index] else trend[index - 1]
        )
        sbt[index] = (
            lower.iloc[index] if trend[index] > 0 else upper.iloc[index] if trend[index] < 0 else basis.iloc[index]
        )
    previous = np.concatenate(([0], trend[:-1]))
    sbt_up, sbt_down = np.where(trend > 0, sbt, np.nan), np.where(trend < 0, sbt, np.nan)
    zigzag = np.full(len(df), np.nan)
    last_turn = np.nan
    for index in range(len(df)):
        if trend[index] != 0 and trend[index] != previous[index]:
            last_turn = closes[index]
        if np.isfinite(last_turn):
            zigzag[index] = last_turn
    zigzag_diff = np.concatenate(([np.nan], np.diff(zigzag)))
    trend_buy, trend_sell = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    buys = (closes > upper.to_numpy()) & (previous <= 0) if deviation_mode == "bollinger" else trend_buy
    sells = (closes < lower.to_numpy()) & (previous >= 0) if deviation_mode == "bollinger" else trend_sell
    if signal_mode == "zigzag":
        buys, sells = trend_buy & (zigzag_diff > 0), trend_sell & (zigzag_diff < 0)
    plots = [
        _line("sbt_up", "SBT Up", sbt_up, overlay=True, color="#00bcd4"),
        _line("sbt_down", "SBT Down", sbt_down, overlay=True, color="#ff5252"),
    ]
    if show_zigzag:
        plots.append(_line("sbt_zigzag", "ZigZag", zigzag, overlay=True, color="#9e9e9e"))
    if show_tp:
        plots.append(
            _line(
                "sbt_take_profit",
                "Take Profit",
                basis if tp_type == "basis" else (upper + lower) / 2,
                overlay=True,
                color="#ff9800",
            )
        )
    return {
        **_output("SuperBollingerTrend", plots),
        "signals": [
            {
                "type": "buy",
                "text": "Buy",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00c853",
            },
            {
                "type": "sell",
                "text": "Sell",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


compute = _super_bollinger
