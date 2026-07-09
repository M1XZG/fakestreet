"""Frankfurter fiat provider with latest-rate fallback."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

import requests


FRANKFURTER_URL = "https://api.frankfurter.dev/v1"
FALLBACK_URL = "https://open.er-api.com/v6/latest/USD"
TIMEOUT = 12
HISTORY_DAYS = {"1d": 1, "5d": 5, "1mo": 30, "6mo": 180, "1y": 365}


def _invert_rates(rates: dict, symbols: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for symbol in symbols:
        rate = rates.get(symbol)
        if rate:
            out[symbol] = 1.0 / float(rate)
    return out


def _frankfurter_latest(symbols: List[str]) -> Dict[str, float]:
    response = requests.get(
        f"{FRANKFURTER_URL}/latest",
        params={"base": "USD", "symbols": ",".join(symbols)},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return _invert_rates(response.json().get("rates") or {}, symbols)


def _frankfurter_on(day: date, symbols: List[str]) -> Dict[str, float]:
    response = requests.get(
        f"{FRANKFURTER_URL}/{day.isoformat()}",
        params={"base": "USD", "symbols": ",".join(symbols)},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return _invert_rates(response.json().get("rates") or {}, symbols)


def _fallback_latest(symbols: List[str]) -> Dict[str, float]:
    response = requests.get(FALLBACK_URL, timeout=TIMEOUT)
    response.raise_for_status()
    return _invert_rates(response.json().get("rates") or {}, symbols)


def get_quotes(symbols: List[str]) -> Dict[str, Tuple[float, float]]:
    if not symbols:
        return {}
    today = date.today()
    previous_day = today - timedelta(days=1)
    try:
        latest = _frankfurter_latest(symbols)
        previous = _frankfurter_on(previous_day, symbols)
    except Exception:
        latest = _fallback_latest(symbols)
        previous = latest
    return {
        symbol: (latest[symbol], previous.get(symbol, latest[symbol]))
        for symbol in symbols
        if symbol in latest
    }


def supported() -> Dict[str, str]:
    try:
        response = requests.get(f"{FRANKFURTER_URL}/currencies", timeout=TIMEOUT)
        response.raise_for_status()
        return {str(code).upper(): str(name) for code, name in response.json().items()}
    except Exception:
        return {}


def search(query: str) -> List[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    results: List[dict] = []
    for code, name in sorted(supported().items()):
        if q in code.lower() or q in name.lower():
            results.append({"symbol": code, "name": name, "provider_id": code})
    return results


def get_history(symbol: str, range: str = "1mo") -> List[Tuple[int, float]]:
    days = HISTORY_DAYS.get(range, HISTORY_DAYS["1mo"])
    end = date.today()
    start = end - timedelta(days=days)
    try:
        response = requests.get(
            f"{FRANKFURTER_URL}/{start.isoformat()}..{end.isoformat()}",
            params={"base": "USD", "symbols": symbol},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        rates = response.json().get("rates") or {}
        points: List[Tuple[int, float]] = []
        for day, row in sorted(rates.items()):
            rate = (row or {}).get(symbol)
            if rate:
                dt = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
                points.append((int(dt.timestamp()), 1.0 / float(rate)))
        return points
    except Exception:
        return []
