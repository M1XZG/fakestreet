"""FastAPI application for the local paper-trading game."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from app import auth
from app import registry
from app.db import init_db
from app.game import (
    NotFoundError,
    UsernameTakenError,
    authenticate,
    execute_trade,
    get_leaderboard,
    get_player,
    get_portfolio,
    get_transactions,
    register_player,
    reset_password,
)
from app.market import market
from app.models import AddAssetRequest, LoginRequest, RecoverRequest, RegisterRequest, TradeRequest
from app.providers import crypto, fiat, stocks

app = FastAPI(title="Trading Game")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


class AuthError(Exception):
    """Raised for missing/invalid tokens (401) or wrong-account access (403)."""

    def __init__(self, message: str = "Not signed in", status_code: int = 401) -> None:
        self.message = message
        self.status_code = status_code


@app.exception_handler(AuthError)
async def _auth_error_handler(_request, exc: AuthError):
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "message": exc.message})


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def current_player_id(authorization: str | None = Header(default=None)) -> int:
    player_id = auth.resolve_token(_extract_token(authorization))
    if player_id is None:
        raise AuthError("Not signed in", 401)
    return player_id


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/assets")
def assets() -> dict:
    custom = registry.custom_symbols()
    rows = []
    for asset in market.get_assets():
        row = asset.to_dict()
        row["custom"] = row["symbol"] in custom
        rows.append(row)
    return {
        "base_currency": config.BASE_CURRENCY,
        "as_of": int(time.time()),
        "assets": rows,
    }


@app.get("/api/assets/search")
def asset_search(klass: str = Query(alias="class"), q: str = Query(default="")) -> dict:
    klass = (klass or "").strip().lower()
    if klass not in {"stock", "crypto", "fiat"}:
        return JSONResponse(status_code=400, content={"ok": False, "message": "Pick stock, crypto, or fiat"})
    if klass == "stock":
        results = stocks.search(q)
    elif klass == "crypto":
        results = crypto.search(q)
    else:
        results = fiat.search(q)
    return {"class": klass, "results": results}


@app.post("/api/assets")
def add_asset(body: AddAssetRequest, current: int = Depends(current_player_id)):
    try:
        registry.create_custom_asset(
            body.asset_class,
            body.symbol,
            provider_id=body.provider_id,
            name=body.name,
            added_by=current,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})

    symbol = body.symbol.strip().upper()
    asset = registry.get_asset(symbol)
    price = 0.0
    prev_close = 0.0
    try:
        price = float(market.get_price(symbol))
        cached = market._cache.get(symbol) or {}
        prev_close = float(cached.get("prev_close") or price)
    except Exception:
        pass
    response_asset = {
        "symbol": asset["symbol"],
        "name": asset["name"],
        "asset_class": asset["asset_class"],
        "provider_id": asset["provider_id"],
        "price": round(price, 6),
        "prev_close": round(prev_close, 6),
        "change_pct": round(0.0 if not prev_close else (price / prev_close - 1.0) * 100.0, 2),
        "custom": True,
    }
    return {"ok": True, "asset": response_asset}


@app.get("/api/assets/{symbol}/history")
def asset_history(symbol: str, range: str = Query(default=config.HISTORY_DEFAULT_RANGE)) -> dict:
    symbol = symbol.strip().upper()
    try:
        history = market.get_history(symbol, range=range)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    return {
        "symbol": symbol,
        "range": range,
        "points": [{"t": int(ts), "price": float(price)} for ts, price in history],
    }


@app.post("/api/register")
def register(body: RegisterRequest):
    try:
        return register_player(body.username, body.password, body.recovery_word)
    except (UsernameTakenError, ValueError) as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})


@app.post("/api/login")
def login(body: LoginRequest):
    result = authenticate(body.username, body.password)
    if result is None:
        return JSONResponse(status_code=401, content={"ok": False, "message": "Wrong username or password"})
    return result


@app.post("/api/recover")
def recover(body: RecoverRequest):
    try:
        result = reset_password(body.username, body.recovery_word, body.new_password)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
    if result is None:
        return JSONResponse(status_code=401, content={"ok": False, "message": "That memorable word doesn't match"})
    return result


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    auth.delete_session(_extract_token(authorization))
    return {"ok": True}


@app.get("/api/me")
def me(player_id: int = Depends(current_player_id)):
    player = get_player(player_id)
    if player is None:
        raise AuthError("Not signed in", 401)
    return {"id": player["id"], "username": player["username"]}


@app.get("/api/players/{player_id}/portfolio")
def player_portfolio(player_id: int, current: int = Depends(current_player_id)) -> dict:
    if player_id != current:
        raise AuthError("That's not your account", 403)
    try:
        return get_portfolio(player_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/players/{player_id}/transactions")
def player_transactions(
    player_id: int,
    current: int = Depends(current_player_id),
    limit: int = Query(default=100),
) -> dict:
    if player_id != current:
        raise AuthError("That's not your account", 403)
    try:
        return {"player_id": player_id, "transactions": get_transactions(player_id, limit=limit)}
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/trade")
def trade(body: TradeRequest, current: int = Depends(current_player_id)):
    try:
        ok, message, execution, cash = execute_trade(current, body.symbol, body.side, body.quantity)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    content = {"ok": ok, "message": message}
    if ok:
        content["execution"] = execution
        content["cash"] = cash
        return content
    return JSONResponse(status_code=400, content=content)


@app.get("/api/leaderboard")
def leaderboard() -> dict:
    return {"leaderboard": get_leaderboard()}


_WEB_DIR = Path(__file__).resolve().parents[1] / "web"
app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
