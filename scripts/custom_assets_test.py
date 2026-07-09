#!/usr/bin/env python3
"""Live test of the user-added-assets feature against a running server."""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
passed = failed = 0


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
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


# baseline count
s, j = call("GET", "/api/assets")
base_count = len(j.get("assets", []))
print(f"baseline assets: {base_count}\n")

# sign in
u = f"custom_{int(time.time())}"
s, j = call("POST", "/api/register", {"username": u, "password": "hunter2", "recovery_word": "word"})
tok = j.get("token")
check("registered", s == 200 and bool(tok), f"{s} {j}")

# search
s, j = call("GET", "/api/assets/search?class=crypto&q=pepe")
pepe = next((r for r in j.get("results", []) if r["provider_id"] == "pepe"), None)
check("crypto search finds pepe", pepe is not None, str(j)[:200])
s, j = call("GET", "/api/assets/search?class=fiat&q=kro")
check("fiat search finds krona(s)", any(r["symbol"] in ("SEK", "NOK", "DKK") for r in j.get("results", [])), str(j)[:200])
s, j = call("GET", "/api/assets/search?class=stock&q=alibaba")
check("stock search returns results", len(j.get("results", [])) > 0, str(j)[:160])

# add stock (BABA), crypto (pepe), fiat (SEK)
s, j = call("POST", "/api/assets", {"asset_class": "stock", "symbol": "BABA"}, token=tok)
check("add stock BABA ok+priced+custom", s == 200 and j.get("ok") and j["asset"]["price"] > 0 and j["asset"]["custom"] is True, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "crypto", "symbol": "PEPE", "provider_id": "pepe", "name": "Pepe"}, token=tok)
check("add crypto PEPE ok", s == 200 and j.get("ok") and j["asset"]["price"] > 0, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "fiat", "symbol": "SEK"}, token=tok)
check("add fiat SEK ok", s == 200 and j.get("ok") and j["asset"]["price"] > 0, f"{s} {j}")

# now present in /api/assets with custom flag
s, j = call("GET", "/api/assets")
bym = {a["symbol"]: a for a in j.get("assets", [])}
check("asset count grew by 3", len(j.get("assets", [])) == base_count + 3, f"{len(j.get('assets', []))} vs {base_count}")
check("BABA present + custom", bym.get("BABA", {}).get("custom") is True, str(bym.get("BABA")))
check("PEPE present + custom", bym.get("PEPE", {}).get("custom") is True, str(bym.get("PEPE")))
check("SEK present + custom", bym.get("SEK", {}).get("custom") is True, str(bym.get("SEK")))
check("built-in AAPL not flagged custom", bym.get("AAPL", {}).get("custom") in (False, None), str(bym.get("AAPL")))

# history + trade a custom asset
s, j = call("GET", "/api/assets/BABA/history?range=1mo")
check("custom BABA history non-empty", s == 200 and len(j.get("points", [])) > 0, str(s))
s, j = call("POST", "/api/trade", {"symbol": "BABA", "side": "buy", "quantity": 3}, token=tok)
check("buy custom BABA ok", s == 200 and j.get("ok"), f"{s} {j}")
s, j = call("GET", f"/api/players/{call('GET','/api/me',token=tok)[1]['id']}/portfolio", token=tok)
baba = next((h for h in j.get("holdings", []) if h["symbol"] == "BABA"), None)
check("BABA in portfolio with real name", baba is not None and len(baba.get("name", "")) > 3, str(baba))

# negatives
s, j = call("POST", "/api/assets", {"asset_class": "stock", "symbol": "BABA"}, token=tok)
check("duplicate add -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "stock", "symbol": "AAPL"}, token=tok)
check("add existing built-in -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "stock", "symbol": "ZZZZQQ"}, token=tok)
check("bogus ticker -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "banana", "symbol": "XYZ"}, token=tok)
check("bad class -> 400", s == 400 and j.get("ok") is False, f"{s} {j}")
s, j = call("POST", "/api/assets", {"asset_class": "stock", "symbol": "TSM"})
check("add without token -> 401", s == 401, f"{s} {j}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
