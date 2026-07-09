"""Game rules and persistence for the paper-trading backend."""
from __future__ import annotations

import math
import sqlite3
import threading
import time
from collections import defaultdict
from typing import Any

import config
from app import auth
from app import registry
from app.db import get_conn
from app.market import market

_trade_lock = threading.Lock()

MIN_PASSWORD_LEN = 4


class NotFoundError(Exception):
    """Raised when a requested game resource does not exist."""


class UsernameTakenError(Exception):
    """Raised when registering a username that is already in use."""


def _now() -> int:
    return int(time.time())


def _row_to_dict(row) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _money(value: float) -> float:
    return round(float(value), 6)


def _pct(value: float) -> float:
    return round(float(value), 4)


def _format_qty(quantity: float) -> str:
    return f"{quantity:g}"


def register_player(username: str, password: str, recovery_word: str) -> dict[str, Any]:
    username = (username or "").strip()
    if not username:
        raise ValueError("Username is required")
    if len(username) > 40:
        raise ValueError("Username must be 40 characters or fewer")
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
    recovery = auth.normalize_recovery(recovery_word)
    if not recovery:
        raise ValueError("A memorable word is required")

    created_at = _now()
    password_hash = auth.hash_secret(password)
    recovery_hash = auth.hash_secret(recovery)

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO players (username, cash, created_at, password_hash, recovery_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, float(config.STARTING_CASH), created_at, password_hash, recovery_hash),
        )
        conn.commit()
        player_id = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        raise UsernameTakenError("Username already taken")
    finally:
        conn.close()

    token = auth.create_session(player_id)
    return {"id": player_id, "username": username, "token": token}


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    username = (username or "").strip()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash FROM players WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if row is None or not auth.verify_secret(password or "", row["password_hash"]):
        return None
    token = auth.create_session(int(row["id"]))
    return {"id": int(row["id"]), "username": row["username"], "token": token}


def reset_password(username: str, recovery_word: str, new_password: str) -> dict[str, Any] | None:
    username = (username or "").strip()
    if not new_password or len(new_password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
    recovery = auth.normalize_recovery(recovery_word)

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, recovery_hash FROM players WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None or not auth.verify_secret(recovery, row["recovery_hash"]):
            return None
        player_id = int(row["id"])
        uname = row["username"]
        conn.execute(
            "UPDATE players SET password_hash = ? WHERE id = ?",
            (auth.hash_secret(new_password), player_id),
        )
        conn.commit()
    finally:
        conn.close()

    # a successful reset drops any old sessions, then signs the player in fresh
    auth.delete_sessions_for_player(player_id)
    token = auth.create_session(player_id)
    return {"id": player_id, "username": uname, "token": token}


def get_player(player_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, cash, created_at FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()
    return _row_to_dict(row)


def get_portfolio(player_id: int) -> dict[str, Any]:
    player = get_player(player_id)
    if player is None:
        raise NotFoundError("Player not found")

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, quantity, avg_cost FROM holdings WHERE player_id = ? ORDER BY symbol",
            (player_id,),
        ).fetchall()

    symbols = [row["symbol"] for row in rows]
    prices = market.get_prices(symbols) if symbols else {}
    holdings = []
    holdings_value = 0.0

    for row in rows:
        symbol = row["symbol"]
        asset = registry.get_asset(symbol) or {"name": symbol, "asset_class": "unknown"}
        quantity = float(row["quantity"])
        avg_cost = float(row["avg_cost"])
        price = float(prices.get(symbol, 0.0))
        value = quantity * price
        cost_basis = quantity * avg_cost
        pl = value - cost_basis
        pl_pct = 0.0 if avg_cost == 0 else (price / avg_cost - 1.0) * 100.0
        holdings_value += value
        holdings.append(
            {
                "symbol": symbol,
                "name": asset["name"],
                "asset_class": asset["asset_class"],
                "quantity": quantity,
                "avg_cost": _money(avg_cost),
                "price": _money(price),
                "value": _money(value),
                "cost_basis": _money(cost_basis),
                "pl": _money(pl),
                "pl_pct": _pct(pl_pct),
            }
        )

    cash = float(player["cash"])
    net_worth = cash + holdings_value
    total_pl = net_worth - float(config.STARTING_CASH)
    total_pl_pct = (total_pl / float(config.STARTING_CASH)) * 100.0 if config.STARTING_CASH else 0.0
    return {
        "player_id": player["id"],
        "username": player["username"],
        "cash": _money(cash),
        "holdings": holdings,
        "holdings_value": _money(holdings_value),
        "net_worth": _money(net_worth),
        "starting_cash": float(config.STARTING_CASH),
        "total_pl": _money(total_pl),
        "total_pl_pct": _pct(total_pl_pct),
    }


def execute_trade(player_id: int, symbol: str, side: str, quantity: float) -> tuple[bool, str, dict[str, Any] | None, float]:
    symbol = symbol.strip().upper() if isinstance(symbol, str) else symbol
    side = side.strip().lower() if isinstance(side, str) else side

    with _trade_lock:
        conn = get_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            player = conn.execute(
                "SELECT id, cash FROM players WHERE id = ?",
                (player_id,),
            ).fetchone()
            if player is None:
                raise NotFoundError("Player not found")

            cash = float(player["cash"])
            if registry.get_asset(symbol) is None:
                conn.rollback()
                return False, f"Unknown symbol: {symbol}", None, cash

            if not isinstance(quantity, (int, float)) or not math.isfinite(float(quantity)) or float(quantity) <= 0:
                conn.rollback()
                return False, "Quantity must be greater than 0", None, cash
            quantity = float(quantity)

            if side not in {"buy", "sell"}:
                conn.rollback()
                return False, "Side must be buy or sell", None, cash

            price = float(market.get_price(symbol))
            total = quantity * price
            ts = _now()

            if side == "buy":
                if cash < total:
                    conn.rollback()
                    return False, f"Insufficient funds: need ${total:,.2f}, have ${cash:,.2f}", None, cash

                holding = conn.execute(
                    "SELECT quantity, avg_cost FROM holdings WHERE player_id = ? AND symbol = ?",
                    (player_id, symbol),
                ).fetchone()
                if holding is None:
                    conn.execute(
                        "INSERT INTO holdings (player_id, symbol, quantity, avg_cost) VALUES (?, ?, ?, ?)",
                        (player_id, symbol, quantity, price),
                    )
                else:
                    old_qty = float(holding["quantity"])
                    old_avg = float(holding["avg_cost"])
                    new_qty = old_qty + quantity
                    new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                    conn.execute(
                        "UPDATE holdings SET quantity = ?, avg_cost = ? WHERE player_id = ? AND symbol = ?",
                        (new_qty, new_avg, player_id, symbol),
                    )
                new_cash = cash - total
                verb = "Bought"
            else:
                holding = conn.execute(
                    "SELECT quantity, avg_cost FROM holdings WHERE player_id = ? AND symbol = ?",
                    (player_id, symbol),
                ).fetchone()
                held = float(holding["quantity"]) if holding is not None else 0.0
                if holding is None or held < quantity - 1e-9:
                    conn.rollback()
                    return False, f"Insufficient {symbol}: you hold {held:g}, tried to sell {quantity:g}", None, cash

                remaining = held - quantity
                if remaining <= 1e-9:
                    conn.execute(
                        "DELETE FROM holdings WHERE player_id = ? AND symbol = ?",
                        (player_id, symbol),
                    )
                else:
                    conn.execute(
                        "UPDATE holdings SET quantity = ? WHERE player_id = ? AND symbol = ?",
                        (remaining, player_id, symbol),
                    )
                new_cash = cash + total
                verb = "Sold"

            conn.execute("UPDATE players SET cash = ? WHERE id = ?", (new_cash, player_id))
            conn.execute(
                "INSERT INTO transactions (player_id, symbol, side, quantity, price, total, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (player_id, symbol, side, quantity, price, total, ts),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    execution = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": _money(price),
        "total": _money(total),
    }
    message = f"{verb} {_format_qty(quantity)} {symbol} @ ${price:,.2f}"
    return True, message, execution, _money(new_cash)


def get_transactions(player_id: int, limit: int = 100) -> list[dict[str, Any]]:
    if get_player(player_id) is None:
        raise NotFoundError("Player not found")
    limit = max(1, min(int(limit), 500))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, side, quantity, price, total, ts FROM transactions WHERE player_id = ? ORDER BY ts DESC, id DESC LIMIT ?",
            (player_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "symbol": row["symbol"],
            "side": row["side"],
            "quantity": float(row["quantity"]),
            "price": _money(row["price"]),
            "total": _money(row["total"]),
            "ts": row["ts"],
        }
        for row in rows
    ]


def get_leaderboard() -> list[dict[str, Any]]:
    with get_conn() as conn:
        players = conn.execute("SELECT id, username, cash FROM players ORDER BY id").fetchall()
        holding_rows = conn.execute("SELECT player_id, symbol, quantity FROM holdings").fetchall()

    symbols = sorted({row["symbol"] for row in holding_rows})
    prices = market.get_prices(symbols) if symbols else {}
    holdings_by_player: dict[int, list[Any]] = defaultdict(list)
    for row in holding_rows:
        holdings_by_player[int(row["player_id"])].append(row)

    ranked = []
    for player in players:
        player_id = int(player["id"])
        holdings_value = sum(
            float(row["quantity"]) * float(prices.get(row["symbol"], 0.0))
            for row in holdings_by_player[player_id]
        )
        net_worth = float(player["cash"]) + holdings_value
        total_pl_pct = ((net_worth - float(config.STARTING_CASH)) / float(config.STARTING_CASH)) * 100.0 if config.STARTING_CASH else 0.0
        ranked.append(
            {
                "player_id": player_id,
                "username": player["username"],
                "net_worth": _money(net_worth),
                "total_pl_pct": _pct(total_pl_pct),
            }
        )

    ranked.sort(key=lambda item: item["net_worth"], reverse=True)
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked
