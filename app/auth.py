"""Password hashing, recovery words, and session tokens.

This is a friendly barrier so players on the local network can't wander into each
other's accounts, not bank-grade security. Even so, passwords and recovery words
are salted and hashed with PBKDF2-HMAC-SHA256 and are never stored in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from app.db import get_conn

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 120_000
_SALT_BYTES = 16


def hash_secret(plain: str) -> str:
    """Return a self-describing hash string: 'pbkdf2_sha256$iters$salt$hash'."""
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_secret(plain: str, stored: str | None) -> bool:
    """Constant-time check of a plaintext secret against a stored hash string."""
    if not stored:
        return False
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), bytes.fromhex(salt_hex), int(iters)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived.hex(), hash_hex)


def normalize_recovery(word: str) -> str:
    """Recovery words match case-insensitively and ignore surrounding space."""
    return (word or "").strip().lower()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def create_session(player_id: int) -> str:
    token = new_token()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (token, player_id, created_at) VALUES (?, ?, ?)",
            (token, int(player_id), int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def resolve_token(token: str | None) -> int | None:
    """Return the player id a token belongs to, or None if unknown/blank."""
    if not token:
        return None
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT player_id FROM sessions WHERE token = ?", (token,)
        ).fetchone()
    finally:
        conn.close()
    return int(row["player_id"]) if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    conn = get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def delete_sessions_for_player(player_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE player_id = ?", (int(player_id),))
        conn.commit()
    finally:
        conn.close()
