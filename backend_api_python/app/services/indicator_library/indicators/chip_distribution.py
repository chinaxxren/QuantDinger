"""Reviewed backend calculation for the chip_distribution indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _number, np, pd


def _chip_distribution(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    """Build a price-level volume profile with candle-direction buy/sell estimates."""
    lookback = _integer(params, "lookback", 120, minimum=10, maximum=5000)
    row_count = _integer(params, "rows", 48, minimum=8, maximum=120)
    value_area_percent = _number(params, "value_area_percent", 70, minimum=50, maximum=99)
    value_area_ratio = value_area_percent / 100.0

    window = df.tail(lookback)
    ohlcv = {
        key: pd.to_numeric(window[key], errors="coerce").to_numpy(dtype=float)
        for key in ("open", "high", "low", "close", "volume")
    }
    valid = np.ones(len(window), dtype=bool)
    for key, values in ohlcv.items():
        valid &= np.isfinite(values)
    valid &= ohlcv["high"] >= ohlcv["low"]
    valid &= ohlcv["volume"] >= 0

    if not valid.any():
        raise ValueError("no valid bars for chip distribution")

    opens = ohlcv["open"][valid]
    highs = ohlcv["high"][valid]
    lows = ohlcv["low"][valid]
    closes = ohlcv["close"][valid]
    volumes = ohlcv["volume"][valid]
    price_low = float(np.min(lows))
    price_high = float(np.max(highs))
    if not np.isfinite(price_high - price_low):
        raise ValueError("chip distribution price range is out of range")

    if price_high <= price_low:
        padding = max(abs(price_low) * 1e-8, 1e-8)
        price_low -= padding
        price_high += padding

    edges = np.linspace(price_low, price_high, row_count + 1, dtype=float)
    buy_volume = np.zeros(row_count, dtype=float)
    sell_volume = np.zeros(row_count, dtype=float)

    for open_price, high, low, close, volume in zip(opens, highs, lows, closes, volumes):
        if volume <= 0:
            continue

        if high <= low:
            bin_index = int(np.clip(np.searchsorted(edges, close, side="right") - 1, 0, row_count - 1))
            buy_share = 1.0 if close > open_price else 0.0 if close < open_price else 0.5
            buy_volume[bin_index] += volume * buy_share
            sell_volume[bin_index] += volume * (1.0 - buy_share)
            continue

        first = max(0, int(np.searchsorted(edges, low, side="right") - 1))
        last = min(row_count - 1, int(np.searchsorted(edges, high, side="left")))
        overlaps = np.maximum(
            0.0,
            np.minimum(edges[first : last + 2], high) - np.maximum(edges[first : last + 2], low),
        )
        overlap_total = float(overlaps.sum())
        if overlap_total <= 0:
            bin_index = int(np.clip(np.searchsorted(edges, low + (high - low) / 2, side="right") - 1, 0, row_count - 1))
            overlaps = np.zeros(last - first + 1, dtype=float)
            overlaps[bin_index - first] = 1.0
            overlap_total = 1.0

        allocations = volume * (overlaps / overlap_total)
        # Keep each candle's assigned volume conserved despite floating-point rounding.
        allocations[-1] += volume - float(allocations.sum())
        if close > open_price:
            buy_volume[first : last + 1] += allocations
        elif close < open_price:
            sell_volume[first : last + 1] += allocations
        else:
            buy_volume[first : last + 1] += allocations * 0.5
            sell_volume[first : last + 1] += allocations * 0.5

    totals = buy_volume + sell_volume
    total_volume = float(totals.sum())
    if not np.isfinite(total_volume):
        raise ValueError("chip distribution volume is out of range")

    rows = []
    for index in range(row_count):
        rows.append(
            {
                "priceLow": float(edges[index]),
                "priceHigh": float(edges[index + 1]),
                "price": float(edges[index] + (edges[index + 1] - edges[index]) / 2),
                "buyVolume": float(buy_volume[index]),
                "sellVolume": float(sell_volume[index]),
                "totalVolume": float(totals[index]),
            }
        )

    poc_index = int(np.argmax(totals))
    target_volume = total_volume * value_area_ratio
    value_area_volume = float(totals[poc_index])
    value_area_low = poc_index
    value_area_high = poc_index
    while value_area_volume < target_volume and (value_area_low > 0 or value_area_high < row_count - 1):
        below = totals[value_area_low - 1] if value_area_low > 0 else -1.0
        above = totals[value_area_high + 1] if value_area_high < row_count - 1 else -1.0
        if above > below:
            value_area_high += 1
            value_area_volume += float(above)
        elif below > above:
            value_area_low -= 1
            value_area_volume += float(below)
        else:
            if value_area_low > 0:
                value_area_low -= 1
                value_area_volume += float(below)
            if value_area_high < row_count - 1 and value_area_volume < target_volume:
                value_area_high += 1
                value_area_volume += float(above)

    current_price = float(closes[-1])
    estimated_profitable_volume = 0.0
    for row in rows:
        if current_price >= row["priceHigh"]:
            estimated_profitable_volume += row["totalVolume"]
        elif current_price > row["priceLow"]:
            row_span = row["priceHigh"] - row["priceLow"]
            if row_span > 0:
                estimated_profitable_volume += row["totalVolume"] * (current_price - row["priceLow"]) / row_span

    profile = {
        "rows": rows,
        "windowBars": int(valid.sum()),
        "totalVolume": total_volume,
        "buyVolume": float(buy_volume.sum()),
        "sellVolume": float(sell_volume.sum()),
        "poc": rows[poc_index]["price"],
        "vah": rows[value_area_high]["priceHigh"],
        "val": rows[value_area_low]["priceLow"],
        "valueAreaPercent": value_area_percent,
        "currentPrice": current_price,
        "estimatedProfitableRatio": (
            float(np.clip(estimated_profitable_volume / total_volume, 0.0, 1.0)) if total_volume > 0 else 0.0
        ),
        "method": "candle_direction_estimate",
    }
    return {"name": "Chip Distribution", "plots": [], "signals": [], "layers": [], "profile": profile}


compute = _chip_distribution
