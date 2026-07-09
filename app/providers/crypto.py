"""CoinGecko crypto provider."""
from __future__ import annotations

from typing import Dict, List, Tuple

import requests


BASE_URL = "https://api.coingecko.com/api/v3"
TIMEOUT = 12
HISTORY_DAYS = {"1d": 1, "5d": 5, "1mo": 30, "6mo": 180, "1y": 365}


def get_quotes(coin_ids: List[str]) -> Dict[str, Tuple[float, float]]:
    if not coin_ids:
        return {}
    response = requests.get(
        f"{BASE_URL}/simple/price",
        params={
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    quotes: Dict[str, Tuple[float, float]] = {}
    for coin_id in coin_ids:
        row = data.get(coin_id) or {}
        price = row.get("usd")
        change = row.get("usd_24h_change")
        if price is None:
            continue
        price_f = float(price)
        if change is None or change <= -100:
            prev_close = price_f
        else:
            prev_close = price_f / (1.0 + float(change) / 100.0)
        quotes[coin_id] = (price_f, prev_close)
    return quotes


def search(query: str, limit: int = 10) -> List[dict]:
    query = (query or "").strip()
    if not query:
        return []
    try:
        response = requests.get(
            f"{BASE_URL}/search",
            params={"query": query},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json().get("coins") or []
    except Exception:
        return []

    results: List[dict] = []
    seen: set[str] = set()
    for row in rows:
        provider_id = str(row.get("id") or "").strip()
        symbol = str(row.get("symbol") or "").strip().upper()
        if not provider_id or not symbol or provider_id in seen:
            continue
        results.append(
            {
                "symbol": symbol,
                "name": str(row.get("name") or symbol),
                "provider_id": provider_id,
            }
        )
        seen.add(provider_id)
        if len(results) >= limit:
            break
    return results


def get_history(coin_id: str, range: str = "1mo") -> List[Tuple[int, float]]:
    days = HISTORY_DAYS.get(range, HISTORY_DAYS["1mo"])
    response = requests.get(
        f"{BASE_URL}/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    points: List[Tuple[int, float]] = []
    for ts_ms, price in data.get("prices") or []:
        if price is not None:
            points.append((int(ts_ms // 1000), float(price)))
    return points
