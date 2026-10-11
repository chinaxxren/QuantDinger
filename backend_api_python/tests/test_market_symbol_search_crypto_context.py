from app.services.market import symbol_search


def test_crypto_search_uses_matching_cached_catalog_without_live_lookup(monkeypatch):
    monkeypatch.setattr(
        symbol_search,
        "_search_crypto_exchange",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live lookup must not run")),
    )
    monkeypatch.setattr(
        symbol_search,
        "_search_cached_crypto_symbols",
        lambda keyword, limit, exchange_id, market_type: [
            {
                "market": "Crypto",
                "symbol": "AAPL/USDT",
                "name": "Apple",
                "exchange_id": exchange_id,
                "market_type": market_type,
                "instrument_id": "AAPL-USDT-SWAP",
                "settle_currency": "USDT",
                "asset_class": "equity",
            }
        ],
    )

    rows = symbol_search.search_market_symbols(
        "Crypto",
        "AAPL",
        exchange_id="okx",
        market_type="swap",
    )

    assert rows == [
        {
            "market": "Crypto",
            "symbol": "AAPL/USDT",
            "name": "Apple",
            "exchange_id": "okx",
            "market_type": "swap",
            "instrument_id": "AAPL-USDT-SWAP",
            "settle_currency": "USDT",
            "asset_class": "equity",
            "product_type": "crypto",
            "api_family": "swap",
            "underlying_market": "",
            "underlying_symbol": "",
            "product_meta": {},
        }
    ]


def test_crypto_search_rejects_removed_exchange():
    assert symbol_search.search_market_symbols(
        "Crypto",
        "BTC",
        exchange_id="retiredexchange",
        market_type="spot",
    ) == []


def test_crypto_search_falls_back_to_public_catalog_when_local_catalog_is_empty(monkeypatch):
    monkeypatch.setattr(
        symbol_search,
        "_search_cached_crypto_symbols",
        lambda keyword, limit, exchange_id, market_type: [],
    )
    monkeypatch.setattr(
        symbol_search,
        "_search_crypto_exchange",
        lambda keyword, limit, existing, exchange_id, market_type, **kwargs: [{
            "market": "Crypto",
            "symbol": "PUMP/USDT",
            "name": "PUMP",
            "exchange_id": exchange_id,
            "market_type": market_type,
            "instrument_id": "PUMPUSDT",
            "settle_currency": "USDT",
        }],
    )

    rows = symbol_search.search_market_symbols(
        "Crypto",
        "pump",
        exchange_id="binance",
        market_type="spot",
    )

    assert rows[0]["symbol"] == "PUMP/USDT"
    assert rows[0]["exchange_id"] == "binance"
    assert rows[0]["market_type"] == "spot"


def test_crypto_exact_lookup_refreshes_public_catalog_when_local_match_is_missing(monkeypatch):
    monkeypatch.setattr(
        symbol_search,
        "_search_cached_crypto_symbols",
        lambda keyword, limit, exchange_id, market_type: [],
    )
    calls = []

    def live_lookup(keyword, limit, existing, exchange_id, market_type, **kwargs):
        calls.append(kwargs.get("force_reload"))
        return [{
            "market": "Crypto",
            "symbol": "PUMP/USDT",
            "name": "PUMP",
            "exchange_id": exchange_id,
            "market_type": market_type,
            "instrument_id": "PUMPUSDT",
            "settle_currency": "USDT",
        }]

    monkeypatch.setattr(symbol_search, "_search_crypto_exchange", live_lookup)

    matched = symbol_search.find_market_symbol(
        "Crypto",
        "PUMP/USDT",
        exchange_id="binance",
        market_type="spot",
    )

    assert matched["symbol"] == "PUMP/USDT"
    assert calls == [True]
