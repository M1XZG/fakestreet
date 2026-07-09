"""Yahoo Finance stock provider."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

import requests


BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 12
MAX_WORKERS = 10
HISTORY_INTERVALS = {
    "1d": ("1d", "5m"),
    "5d": ("5d", "15m"),
    "1mo": ("1mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
}


def _chart(ticker: str, range_: str, interval: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/{ticker}",
        params={"range": range_, "interval": interval},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    result = data.get("chart", {}).get("result") or []
    if not result:
        raise ValueError(f"Yahoo returned no chart result for {ticker}")
    return result[0]


def _quote_one(ticker: str) -> Tuple[str, Tuple[float, float]] | None:
    try:
        result = _chart(ticker, "1d", "1d")
        meta = result.get("meta") or {}
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            return None
        if prev_close is None:
            prev_close = price
        return ticker, (float(price), float(prev_close))
    except Exception:
        return None


def get_quotes(tickers: List[str]) -> Dict[str, Tuple[float, float]]:
    if not tickers:
        return {}
    quotes: Dict[str, Tuple[float, float]] = {}
    # Yahoo has no reliable batch endpoint, so fetch per-symbol but in parallel
    # to keep the first (cold-cache) market load fast even with many stocks.
    workers = min(MAX_WORKERS, len(tickers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(_quote_one, tickers):
            if res is not None:
                quotes[res[0]] = res[1]
    return quotes


def search(query: str, limit: int = 10) -> List[dict]:
    query = (query or "").strip()
    if not query:
        return []
    try:
        response = requests.get(
            SEARCH_URL,
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json().get("quotes") or []
    except Exception:
        return []

    results: List[dict] = []
    seen: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        quote_type = str(row.get("quoteType") or "").upper()
        if not symbol or symbol in seen or quote_type not in {"EQUITY", "ETF"}:
            continue
        name = row.get("shortname") or row.get("longname") or symbol
        results.append({"symbol": symbol, "name": str(name)})
        seen.add(symbol)
        if len(results) >= limit:
            break
    return results


def get_history(ticker: str, range: str = "1mo") -> List[Tuple[int, float]]:
    yahoo_range, interval = HISTORY_INTERVALS.get(range, HISTORY_INTERVALS["1mo"])
    result = _chart(ticker, yahoo_range, interval)
    timestamps = result.get("timestamp") or []
    quotes = result.get("indicators", {}).get("quote") or []
    closes = (quotes[0].get("close") if quotes else None) or []
    points: List[Tuple[int, float]] = []
    for ts, close in zip(timestamps, closes):
        if close is not None:
            points.append((int(ts), float(close)))
    return points
