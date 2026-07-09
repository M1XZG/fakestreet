"""Market data service backed by keyless public providers.

Contract, do not change without updating API_CONTRACT.md and the backend:
    class Asset(symbol, name, asset_class, price, prev_close)
        .change_pct -> float
        .to_dict()  -> dict  (adds "change_pct")
    class MarketService:
        get_assets()                         -> list[Asset]
        get_price(symbol)                    -> float            (USD, raises KeyError if unknown)
        get_prices(symbols: list[str])       -> dict[str, float] (USD, unknowns omitted)
        get_history(symbol, range="1mo")     -> list[tuple[int, float]]  (unix_ts, USD price)
        refresh()                            -> None             (force a cache refresh)

Every price returned anywhere is in USD.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

import config
from app import registry
from app.providers import crypto, fiat, stocks


@dataclass
class Asset:
    symbol: str
    name: str
    asset_class: str          # 'stock' | 'crypto' | 'fiat'
    price: float              # current price in USD
    prev_close: float         # previous close / 24h-ago price in USD

    @property
    def change_pct(self) -> float:
        if not self.prev_close:
            return 0.0
        return (self.price / self.prev_close - 1.0) * 100.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["change_pct"] = round(self.change_pct, 2)
        d["price"] = round(self.price, 6)
        d["prev_close"] = round(self.prev_close, 6)
        return d


class MarketService:
    """Fetches live prices, normalizes everything to USD, caches with a TTL."""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, float]] = {}

    def get_assets(self) -> List[Asset]:
        assets = registry.all_assets()
        self._ensure_prices([a["symbol"] for a in assets])
        out: List[Asset] = []
        for a in assets:
            price, prev_close = self._cached_pair(a["symbol"])
            out.append(Asset(a["symbol"], a["name"], a["asset_class"], price, prev_close))
        return out

    def get_price(self, symbol: str) -> float:
        symbol = symbol.strip().upper()
        if registry.get_asset(symbol) is None:
            raise KeyError(f"Unknown symbol: {symbol}")
        self._ensure_prices([symbol])
        return self._cached_pair(symbol)[0]

    def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        assets_by_symbol = self._assets_by_symbol()
        known = [s for s in symbols if s in assets_by_symbol]
        self._ensure_prices(known)
        return {s: self._cache[s]["price"] for s in known if s in self._cache}

    def get_history(self, symbol: str, range: str = "1mo") -> List[Tuple[int, float]]:
        symbol = symbol.strip().upper()
        asset = registry.get_asset(symbol)
        if asset is None:
            raise KeyError(f"Unknown symbol: {symbol}")
        provider_id = asset["provider_id"]
        try:
            if asset["asset_class"] == "stock":
                return stocks.get_history(provider_id, range)
            if asset["asset_class"] == "crypto":
                return crypto.get_history(provider_id, range)
            if asset["asset_class"] == "fiat":
                return fiat.get_history(provider_id, range)
        except Exception:
            pass
        if symbol in self._cache:
            return [(int(self._cache[symbol]["fetched_at"]), float(self._cache[symbol]["price"]))]
        return []

    def refresh(self) -> None:
        for row in self._cache.values():
            row["fetched_at"] = 0.0
        self._ensure_prices([a["symbol"] for a in registry.all_assets()], force=True)

    def _assets_by_symbol(self) -> Dict[str, dict]:
        return {a["symbol"]: a for a in registry.all_assets()}

    def _cached_pair(self, symbol: str) -> Tuple[float, float]:
        row = self._cache.get(symbol)
        if row is None:
            return 0.0, 0.0
        return float(row["price"]), float(row["prev_close"])

    def _is_fresh(self, symbol: str, now: float) -> bool:
        row = self._cache.get(symbol)
        if not row:
            return False
        return now - row["fetched_at"] < config.CACHE_TTL_SECONDS

    def _ensure_prices(self, symbols: List[str], force: bool = False) -> None:
        now = time.time()
        assets_by_symbol = self._assets_by_symbol()
        needed = [s for s in dict.fromkeys(symbols) if s in assets_by_symbol]
        if not force:
            needed = [s for s in needed if not self._is_fresh(s, now)]
        if not needed:
            return

        by_class: Dict[str, List[str]] = {"stock": [], "crypto": [], "fiat": []}
        for symbol in needed:
            by_class[assets_by_symbol[symbol]["asset_class"]].append(symbol)

        self._fetch_stocks(by_class["stock"], assets_by_symbol)
        self._fetch_crypto(by_class["crypto"], assets_by_symbol)
        self._fetch_fiat(by_class["fiat"], assets_by_symbol)

    def _store_quotes(self, symbol_by_provider_id: Dict[str, str], quotes: Dict[str, Tuple[float, float]]) -> None:
        fetched_at = time.time()
        for provider_id, pair in quotes.items():
            symbol = symbol_by_provider_id.get(provider_id)
            if not symbol:
                continue
            price, prev_close = pair
            if price is None:
                continue
            if prev_close is None:
                prev_close = price
            self._cache[symbol] = {
                "price": float(price),
                "prev_close": float(prev_close),
                "fetched_at": fetched_at,
            }

    def _fetch_stocks(self, symbols: List[str], assets_by_symbol: Dict[str, dict]) -> None:
        if not symbols:
            return
        provider_to_symbol = {assets_by_symbol[s]["provider_id"]: s for s in symbols}
        try:
            self._store_quotes(provider_to_symbol, stocks.get_quotes(list(provider_to_symbol)))
        except Exception:
            return

    def _fetch_crypto(self, symbols: List[str], assets_by_symbol: Dict[str, dict]) -> None:
        if not symbols:
            return
        provider_to_symbol = {assets_by_symbol[s]["provider_id"]: s for s in symbols}
        try:
            self._store_quotes(provider_to_symbol, crypto.get_quotes(list(provider_to_symbol)))
        except Exception:
            return

    def _fetch_fiat(self, symbols: List[str], assets_by_symbol: Dict[str, dict]) -> None:
        if not symbols:
            return
        provider_to_symbol = {assets_by_symbol[s]["provider_id"]: s for s in symbols}
        try:
            self._store_quotes(provider_to_symbol, fiat.get_quotes(list(provider_to_symbol)))
        except Exception:
            return


# Module-level singleton the backend can import directly.
market = MarketService()


if __name__ == "__main__":
    m = MarketService()
    assets = {asset.symbol: asset for asset in m.get_assets()}

    for symbol in ["AAPL", "MSFT", "BTC", "ETH", "EUR", "JPY"]:
        print(assets[symbol].to_dict())

    for symbol in ["AAPL", "BTC", "EUR"]:
        points = m.get_history(symbol)
        print(f"history points for {symbol}: {len(points)}")

    try:
        m.get_price("NOPE")
    except KeyError as exc:
        print(f"unknown symbol raises KeyError: {exc}")

    mixed = m.get_prices(["AAPL", "NOPE"])
    print(f"mixed prices omit unknown: {mixed}")

    first_fetched_at = m._cache["AAPL"]["fetched_at"]
    first_price = m.get_price("AAPL")
    second_price = m.get_price("AAPL")
    second_fetched_at = m._cache["AAPL"]["fetched_at"]
    print(
        "cache hit within TTL:",
        first_fetched_at == second_fetched_at,
        f"AAPL={first_price:.2f}/{second_price:.2f}",
    )
