#!/usr/bin/env python3
"""End-to-end smoke test for the trading game API (with accounts/auth).

Usage: python3 tmp/smoke_test.py [base_url]
Default base_url: http://127.0.0.1:8000

Covers the auth flows (register/login/recover/logout/me), token protection of
player-scoped endpoints, and the full trading loop. Exits non-zero on any fail.
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
passed = 0
failed = 0


def call(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}   {detail}")


print(f"Smoke testing {BASE}\n")

# ---- public endpoints (no token) ----
s, j = call("GET", "/api/health")
check("health 200 ok", s == 200 and j.get("status") == "ok", f"{s} {j}")

s, j = call("GET", "/api/assets")
assets = j.get("assets", [])
classes = {a["asset_class"] for a in assets}
check("assets all three classes", {"stock", "crypto", "fiat"} <= classes, str(classes))
bym = {a["symbol"]: a["price"] for a in assets}
check("BTC price real (>1000)", bym.get("BTC", 0) > 1000, str(bym.get("BTC")))
check("AAPL price real", 10 < bym.get("AAPL", 0) < 10000, str(bym.get("AAPL")))

# ---- register ----
uname = f"smoke_{int(time.time())}"
pw = "hunter2"
word = "Rosebud"
s, j = call("POST", "/api/register", {"username": uname, "password": pw, "recovery_word": word})
token = j.get("token")
pid = j.get("id")
check("register 200 with token+id", s == 200 and bool(token) and isinstance(pid, int), f"{s} {j}")

s, j = call("POST", "/api/register", {"username": uname, "password": pw, "recovery_word": word})
check("duplicate register -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/register", {"username": uname + "x", "password": "no", "recovery_word": word})
check("short password -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/register", {"username": uname + "y", "password": pw, "recovery_word": "  "})
check("missing recovery word -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")

# ---- login ----
s, j = call("POST", "/api/login", {"username": uname, "password": pw})
check("login correct -> token", s == 200 and bool(j.get("token")), f"{s} {j}")

s, j = call("POST", "/api/login", {"username": uname, "password": "wrong"})
check("login wrong password -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/login", {"username": "nobody_here", "password": pw})
check("login unknown user -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")

# ---- /api/me ----
s, j = call("GET", "/api/me", token=token)
check("me with token -> id+username", s == 200 and j.get("id") == pid and j.get("username") == uname, f"{s} {j}")
s, j = call("GET", "/api/me")
check("me without token -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")
s, j = call("GET", "/api/me", token="garbage-token")
check("me with bad token -> 401", s == 401, f"{s} {j}")

# ---- protection on player-scoped endpoints ----
s, j = call("GET", f"/api/players/{pid}/portfolio")
check("portfolio without token -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")
s, j = call("GET", f"/api/players/{pid + 999}/portfolio", token=token)
check("portfolio wrong account -> 403", s == 403 and j.get("ok") is False, f"{s} {j}")
s, j = call("GET", f"/api/players/{pid}/portfolio", token=token)
check("portfolio own account -> 200", s == 200 and j.get("net_worth", 0) > 0, f"{s} {j}")
check("net_worth ~ 100k at start", 99000 < j.get("net_worth", 0) < 101000, str(j.get("net_worth")))

# ---- trading (token, no player_id in body) ----
s, j = call("POST", "/api/trade", {"symbol": "AAPL", "side": "buy", "quantity": 10})
check("trade without token -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "AAPL", "side": "buy", "quantity": 10}, token=token)
check("buy 10 AAPL ok", s == 200 and j.get("ok") is True, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "AAPL", "side": "buy", "quantity": 10_000_000}, token=token)
check("insufficient funds -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "BTC", "side": "buy", "quantity": 0.01}, token=token)
check("fractional BTC buy ok", s == 200 and j.get("ok") is True, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "AAPL", "side": "sell", "quantity": 4}, token=token)
check("sell 4 AAPL ok", s == 200 and j.get("ok") is True, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "AAPL", "side": "sell", "quantity": 1000}, token=token)
check("oversell -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/trade", {"symbol": "BTC", "side": "sell", "quantity": 0.01}, token=token)
check("sell entire BTC ok", s == 200 and j.get("ok") is True, f"{s} {j}")
s, j = call("GET", f"/api/players/{pid}/portfolio", token=token)
check("BTC removed after full sell", "BTC" not in {h["symbol"] for h in j.get("holdings", [])}, str(j.get("holdings")))

s, j = call("GET", f"/api/players/{pid}/portfolio", token=token)
syms = {h["symbol"]: h for h in j.get("holdings", [])}
check("holds AAPL qty 6", abs(syms.get("AAPL", {}).get("quantity", 0) - 6) < 1e-9, str(syms.get("AAPL")))

# transactions
s, j = call("GET", f"/api/players/{pid}/transactions", token=token)
txs = j.get("transactions", [])
check("transactions listed (>=4)", s == 200 and len(txs) >= 4, str(len(txs)))
s, j = call("GET", f"/api/players/{pid}/transactions")
check("transactions without token -> 401", s == 401, str(s))

# ---- recover (forgot password) ----
s, j = call("POST", "/api/recover", {"username": uname, "recovery_word": "nope", "new_password": "brandnew"})
check("recover wrong word -> 401", s == 401 and j.get("ok") is False, f"{s} {j}")

s, j = call("POST", "/api/recover", {"username": uname, "recovery_word": "  rosebud ", "new_password": "brandnew"})
check("recover correct word (case-insensitive) -> token", s == 200 and bool(j.get("token")), f"{s} {j}")
recover_token = j.get("token")

s, j = call("POST", "/api/login", {"username": uname, "password": pw})
check("old password rejected after reset", s == 401, f"{s} {j}")
s, j = call("POST", "/api/login", {"username": uname, "password": "brandnew"})
check("new password works after reset", s == 200 and bool(j.get("token")), f"{s} {j}")

s, j = call("GET", "/api/me", token=token)
check("old session invalidated by reset -> 401", s == 401, f"{s} {j}")
s, j = call("GET", "/api/me", token=recover_token)
check("recover-issued token valid", s == 200 and j.get("id") == pid, f"{s} {j}")

# ---- logout ----
s, j = call("POST", "/api/logout", token=recover_token)
check("logout ok", s == 200 and j.get("ok") is True, f"{s} {j}")
s, j = call("GET", "/api/me", token=recover_token)
check("token invalid after logout -> 401", s == 401, f"{s} {j}")

# ---- leaderboard (public) ----
s, j = call("GET", "/api/leaderboard")
lb = j.get("leaderboard", [])
check("leaderboard non-empty", s == 200 and len(lb) >= 1, str(s))
check("leaderboard has our user", any(r.get("username") == uname for r in lb), "user missing")
check("leaderboard ranked desc", all(lb[i]["net_worth"] >= lb[i + 1]["net_worth"] for i in range(len(lb) - 1)))

# ---- history each class (public) ----
for sym in ("AAPL", "BTC", "EUR"):
    s, j = call("GET", f"/api/assets/{sym}/history?range=1mo")
    check(f"history {sym} non-empty", s == 200 and len(j.get("points", [])) > 0, f"{s}")

# ---- static ----
try:
    with urllib.request.urlopen(BASE + "/", timeout=15) as r:
        html = r.read().decode(errors="ignore")
    check("index.html served at /", "<html" in html.lower() or "<!doctype" in html.lower())
except Exception as e:
    check("index.html served at /", False, str(e))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
