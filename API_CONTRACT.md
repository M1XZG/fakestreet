# API contract

Every part of the game is built against this spec so the frontend, backend, and
market-data layer can be developed in parallel. All money is in USD. All
timestamps are Unix seconds (integers). JSON everywhere.

The backend serves the frontend from `web/` and exposes the API under `/api`.

## Authentication

Accounts are protected by a password, with a memorable recovery word as the
forgot-password path. There is no email. A successful register, login, or
recovery returns an opaque session **token**. The client stores it and sends it
on every protected request as a header:

    Authorization: Bearer <token>

Passwords and recovery words are salted and hashed (PBKDF2-HMAC-SHA256); they are
never stored in plaintext and never returned by any endpoint. The recovery word
is matched case-insensitively (trimmed and lowercased). Usernames are trimmed and
case-sensitive.

Protected endpoints return `401 { "ok": false, "message": "..." }` when the token
is missing or invalid, and `403 { "ok": false, "message": "..." }` when a valid
token is used to reach a different player's data.

## Data shapes

**Asset**
```json
{ "symbol": "AAPL", "name": "Apple", "asset_class": "stock",
  "price": 312.19, "prev_close": 309.90, "change_pct": 0.74 }
```
`asset_class` is one of `stock`, `crypto`, `fiat`. `change_pct` is the percentage
move from `prev_close` to `price`.

**Holding**
```json
{ "symbol": "AAPL", "name": "Apple", "asset_class": "stock",
  "quantity": 10.0, "avg_cost": 300.0, "price": 312.19,
  "value": 3121.90, "cost_basis": 3000.0, "pl": 121.90, "pl_pct": 4.06 }
```

**Transaction**
```json
{ "id": 5, "symbol": "AAPL", "side": "buy", "quantity": 10.0,
  "price": 300.0, "total": 3000.0, "ts": 1783607782 }
```

## Endpoints

### GET /api/health
`200` → `{ "status": "ok" }`

### GET /api/assets
Live snapshot of the whole tradable universe.
`200` →
```json
{ "base_currency": "USD", "as_of": 1783607782, "assets": [ Asset, ... ] }
```
User-added assets appear here too, each flagged with `"custom": true`.

### GET /api/assets/search?class=crypto&q=pepe
Helper to find an asset to add, especially crypto (whose provider ids differ from
their tickers). `class` is `stock`, `crypto`, or `fiat`. Public, no token needed.
`200` →
```json
{ "class": "crypto", "results": [
  { "symbol": "PEPE", "name": "Pepe", "provider_id": "pepe" }, ... ] }
```
For `stock`, results come from Yahoo's symbol search. For `fiat`, results are the
currencies the data source supports. `provider_id` is what you pass back to
`POST /api/assets`.

### POST /api/assets
Add a custom asset to the shared game if it isn't already present. Requires a
bearer token. Body:
`{ "asset_class": "crypto", "symbol": "PEPE", "provider_id": "pepe", "name": "Pepe" }`
- `stock`: `provider_id` defaults to `symbol` (the Yahoo ticker); `name` is looked
  up when omitted.
- `crypto`: `provider_id` is the CoinGecko id (use search to find it); `symbol` is
  the ticker to trade it under.
- `fiat`: `symbol` and `provider_id` are the ISO code; `name` is looked up when omitted.
The server confirms the asset actually prices with its provider before saving.
`200` → `{ "ok": true, "asset": { Asset, "custom": true } }`
`400` → `{ "ok": false, "message": "..." }` (already exists, doesn't resolve,
unsupported currency, or bad class). `401` if not signed in.

### GET /api/assets/{symbol}/history?range=1mo
Historical prices for charting. `range` accepts `1d`, `5d`, `1mo`, `6mo`, `1y`.
`200` →
```json
{ "symbol": "AAPL", "range": "1mo",
  "points": [ { "t": 1783000000, "price": 300.1 }, ... ] }
```
`404` → `{ "detail": "Unknown symbol: XYZ" }`

### POST /api/register
Create a new account and sign in. Body:
`{ "username": "alice", "password": "hunter2", "recovery_word": "rosebud" }`
`200` → `{ "id": 1, "username": "alice", "token": "…" }`
`400` → `{ "ok": false, "message": "Username already taken" }` (also for missing
fields or a password shorter than 4 characters).

### POST /api/login
Body: `{ "username": "alice", "password": "hunter2" }`
`200` → `{ "id": 1, "username": "alice", "token": "…" }`
`401` → `{ "ok": false, "message": "Wrong username or password" }`

### POST /api/recover
Reset a forgotten password using the memorable word; on success it signs you in
with a fresh token. Body:
`{ "username": "alice", "recovery_word": "rosebud", "new_password": "hunter3" }`
`200` → `{ "id": 1, "username": "alice", "token": "…" }`
`401` → `{ "ok": false, "message": "That memorable word doesn't match" }`
`400` → `{ "ok": false, "message": "..." }` (missing fields / password too short)

### POST /api/logout
Header: `Authorization: Bearer <token>`. Invalidates the token.
`200` → `{ "ok": true }`

### GET /api/me
Header: `Authorization: Bearer <token>`. Used on reload to confirm a saved token
is still valid and recover the player id.
`200` → `{ "id": 1, "username": "alice" }`
`401` → `{ "ok": false, "message": "Not signed in" }`

### GET /api/players/{id}/portfolio
Requires a bearer token; `{id}` must be your own account.
`200` →
```json
{ "player_id": 1, "username": "alice", "cash": 95000.0,
  "holdings": [ Holding, ... ], "holdings_value": 3121.90,
  "net_worth": 98121.90, "starting_cash": 100000.0,
  "total_pl": -1878.10, "total_pl_pct": -1.88 }
```
`net_worth = cash + holdings_value`. `total_pl` is net worth minus starting cash.
`401` → not signed in. `403` → the token belongs to a different player.
`404` → `{ "detail": "Player not found" }`

### GET /api/players/{id}/transactions?limit=100
Requires a bearer token; `{id}` must be your own account. Newest first.
`200` → `{ "player_id": 1, "transactions": [ Transaction, ... ] }`
`401` → not signed in. `403` → the token belongs to a different player.
`404` → `{ "detail": "Player not found" }`

### POST /api/trade
Requires a bearer token. The player is taken from the token, so the body carries
only the order:
Body: `{ "symbol": "AAPL", "side": "buy", "quantity": 10 }`.
`side` is `buy` or `sell`. `quantity` must be > 0 and may be fractional. Trades
execute at the current live price. `401` if not signed in.
`200` →
```json
{ "ok": true, "message": "Bought 10 AAPL @ $312.19",
  "execution": { "symbol": "AAPL", "side": "buy", "quantity": 10.0,
                 "price": 312.19, "total": 3121.90 },
  "cash": 91878.10 }
```
`400` (validation: bad quantity, unknown symbol, insufficient funds, insufficient
holdings) → `{ "ok": false, "message": "Insufficient funds: need $3121.90, have $500.00" }`

The 400 body deliberately uses `{ "ok": false, "message": ... }` rather than the
FastAPI default so the frontend can show one field for both success and failure.

### GET /api/leaderboard
Players ranked by net worth, highest first.
`200` →
```json
{ "leaderboard": [ { "rank": 1, "player_id": 1, "username": "alice",
    "net_worth": 98121.90, "total_pl_pct": -1.88 }, ... ] }
```

### Static
- `GET /` → `web/index.html`
- other static assets served from `web/` (e.g. `/app.js`, `/style.css`, `/vendor/chart.umd.min.js`)

## Notes for implementers
- Backend imports the market layer as `from app.market import MarketService`
  (or the module singleton `from app.market import market`). Never call data
  providers from the frontend.
- Prices move between calls; value a portfolio with a single batched
  `get_prices(...)` so all holdings use one consistent snapshot.
- Run the server from the project root so `import config` resolves.
