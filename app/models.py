"""Request models for the FastAPI routes."""
from __future__ import annotations

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    recovery_word: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RecoverRequest(BaseModel):
    username: str
    recovery_word: str
    new_password: str


class TradeRequest(BaseModel):
    symbol: str
    side: str
    quantity: float


class AddAssetRequest(BaseModel):
    asset_class: str
    symbol: str
    provider_id: str | None = None
    name: str | None = None
