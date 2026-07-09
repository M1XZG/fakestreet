"""Shared configuration and the tradable asset universe.

This module is the single source of truth for every part of the game. The
market-data layer reads ASSETS to know what to price, the backend reads it to
expose the market and to look up provider ids, and the frontend receives it
over the API. All monetary values in the whole game are expressed in USD.

Run the server from the project root so that `import config` resolves here.
"""

import os


def _env(name: str, default):
    """Read an env override, falling back to the default when unset/empty."""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


# --- Core settings -----------------------------------------------------------
# Every setting can be overridden with an environment variable (handy for Docker).
BASE_CURRENCY = "USD"
STARTING_CASH = float(_env("TRADING_GAME_STARTING_CASH", 100_000.0))  # starting virtual cash
CACHE_TTL_SECONDS = int(_env("TRADING_GAME_CACHE_TTL", 60))           # how long a fetched price stays fresh
HISTORY_DEFAULT_RANGE = "1mo"                                         # default range for price-history charts
DB_PATH = _env("TRADING_GAME_DB", "trading_game.db")                 # sqlite file; absolute, or relative to project root
HOST = _env("TRADING_GAME_HOST", "0.0.0.0")                          # bind on all interfaces for the local network
PORT = int(_env("TRADING_GAME_PORT", 8000))

# --- Asset universe ----------------------------------------------------------
# provider_id is what the underlying data provider expects:
#   stock -> Yahoo Finance ticker (e.g. "AAPL")
#   crypto -> CoinGecko coin id (e.g. "bitcoin")
#   fiat  -> ISO 4217 code priced in USD via Frankfurter (e.g. "EUR")
ASSETS = [
    # Stocks (Yahoo Finance)
    {"symbol": "AAPL",  "name": "Apple",              "asset_class": "stock",  "provider_id": "AAPL"},
    {"symbol": "MSFT",  "name": "Microsoft",          "asset_class": "stock",  "provider_id": "MSFT"},
    {"symbol": "GOOGL", "name": "Alphabet",           "asset_class": "stock",  "provider_id": "GOOGL"},
    {"symbol": "AMZN",  "name": "Amazon",             "asset_class": "stock",  "provider_id": "AMZN"},
    {"symbol": "TSLA",  "name": "Tesla",              "asset_class": "stock",  "provider_id": "TSLA"},
    {"symbol": "NVDA",  "name": "NVIDIA",             "asset_class": "stock",  "provider_id": "NVDA"},
    {"symbol": "META",  "name": "Meta Platforms",     "asset_class": "stock",  "provider_id": "META"},
    {"symbol": "NFLX",  "name": "Netflix",            "asset_class": "stock",  "provider_id": "NFLX"},
    {"symbol": "DIS",   "name": "Disney",             "asset_class": "stock",  "provider_id": "DIS"},
    {"symbol": "KO",    "name": "Coca-Cola",          "asset_class": "stock",  "provider_id": "KO"},

    # More stocks (added 2026-07-09)
    {"symbol": "JPM", "name": "JPMorgan Chase", "asset_class": "stock", "provider_id": "JPM"},
    {"symbol": "BAC", "name": "Bank of America", "asset_class": "stock", "provider_id": "BAC"},
    {"symbol": "WFC", "name": "Wells Fargo", "asset_class": "stock", "provider_id": "WFC"},
    {"symbol": "GS", "name": "Goldman Sachs", "asset_class": "stock", "provider_id": "GS"},
    {"symbol": "WMT", "name": "Walmart", "asset_class": "stock", "provider_id": "WMT"},
    {"symbol": "COST", "name": "Costco", "asset_class": "stock", "provider_id": "COST"},
    {"symbol": "HD", "name": "Home Depot", "asset_class": "stock", "provider_id": "HD"},
    {"symbol": "MCD", "name": "McDonald's", "asset_class": "stock", "provider_id": "MCD"},
    {"symbol": "SBUX", "name": "Starbucks", "asset_class": "stock", "provider_id": "SBUX"},
    {"symbol": "NKE", "name": "Nike", "asset_class": "stock", "provider_id": "NKE"},
    {"symbol": "PG", "name": "Procter & Gamble", "asset_class": "stock", "provider_id": "PG"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "asset_class": "stock", "provider_id": "JNJ"},
    {"symbol": "PFE", "name": "Pfizer", "asset_class": "stock", "provider_id": "PFE"},
    {"symbol": "UNH", "name": "UnitedHealth", "asset_class": "stock", "provider_id": "UNH"},
    {"symbol": "XOM", "name": "ExxonMobil", "asset_class": "stock", "provider_id": "XOM"},
    {"symbol": "INTC", "name": "Intel", "asset_class": "stock", "provider_id": "INTC"},
    {"symbol": "AMD", "name": "AMD", "asset_class": "stock", "provider_id": "AMD"},
    {"symbol": "CRM", "name": "Salesforce", "asset_class": "stock", "provider_id": "CRM"},
    {"symbol": "ADBE", "name": "Adobe", "asset_class": "stock", "provider_id": "ADBE"},
    {"symbol": "GE", "name": "GE Aerospace", "asset_class": "stock", "provider_id": "GE"},
    {"symbol": "BA", "name": "Boeing", "asset_class": "stock", "provider_id": "BA"},
    {"symbol": "T", "name": "AT&T", "asset_class": "stock", "provider_id": "T"},
    {"symbol": "UBER", "name": "Uber", "asset_class": "stock", "provider_id": "UBER"},
    {"symbol": "COIN", "name": "Coinbase", "asset_class": "stock", "provider_id": "COIN"},
    {"symbol": "PLTR", "name": "Palantir", "asset_class": "stock", "provider_id": "PLTR"},
    {"symbol": "SHOP", "name": "Shopify", "asset_class": "stock", "provider_id": "SHOP"},
    {"symbol": "ABNB", "name": "Airbnb", "asset_class": "stock", "provider_id": "ABNB"},
    {"symbol": "SOFI", "name": "SoFi Technologies", "asset_class": "stock", "provider_id": "SOFI"},
    {"symbol": "HOOD", "name": "Robinhood", "asset_class": "stock", "provider_id": "HOOD"},
    {"symbol": "PINS", "name": "Pinterest", "asset_class": "stock", "provider_id": "PINS"},
    {"symbol": "RBLX", "name": "Roblox", "asset_class": "stock", "provider_id": "RBLX"},
    {"symbol": "DKNG", "name": "DraftKings", "asset_class": "stock", "provider_id": "DKNG"},
    {"symbol": "F", "name": "Ford", "asset_class": "stock", "provider_id": "F"},
    {"symbol": "GM", "name": "General Motors", "asset_class": "stock", "provider_id": "GM"},
    {"symbol": "RIVN", "name": "Rivian", "asset_class": "stock", "provider_id": "RIVN"},
    {"symbol": "FCEL", "name": "FuelCell Energy", "asset_class": "stock", "provider_id": "FCEL"},
    {"symbol": "GSAT", "name": "Globalstar", "asset_class": "stock", "provider_id": "GSAT"},
    {"symbol": "MARA", "name": "MARA Holdings", "asset_class": "stock", "provider_id": "MARA"},
    {"symbol": "RIOT", "name": "Riot Platforms", "asset_class": "stock", "provider_id": "RIOT"},
    {"symbol": "NOK", "name": "Nokia", "asset_class": "stock", "provider_id": "NOK"},
    {"symbol": "VALE", "name": "Vale", "asset_class": "stock", "provider_id": "VALE"},

    # Low-priced / penny stocks (all traded under ~$6 at time of adding)
    {"symbol": "SNDL", "name": "SNDL Inc", "asset_class": "stock", "provider_id": "SNDL"},
    {"symbol": "AMC", "name": "AMC Entertainment", "asset_class": "stock", "provider_id": "AMC"},
    {"symbol": "PLUG", "name": "Plug Power", "asset_class": "stock", "provider_id": "PLUG"},
    {"symbol": "BBD", "name": "Banco Bradesco", "asset_class": "stock", "provider_id": "BBD"},
    {"symbol": "SNAP", "name": "Snap", "asset_class": "stock", "provider_id": "SNAP"},
    {"symbol": "NIO", "name": "NIO", "asset_class": "stock", "provider_id": "NIO"},
    {"symbol": "RIG", "name": "Transocean", "asset_class": "stock", "provider_id": "RIG"},
    {"symbol": "CHPT", "name": "ChargePoint", "asset_class": "stock", "provider_id": "CHPT"},
    {"symbol": "LCID", "name": "Lucid Group", "asset_class": "stock", "provider_id": "LCID"},

    # Crypto (CoinGecko)
    {"symbol": "BTC",   "name": "Bitcoin",            "asset_class": "crypto", "provider_id": "bitcoin"},
    {"symbol": "ETH",   "name": "Ethereum",           "asset_class": "crypto", "provider_id": "ethereum"},
    {"symbol": "SOL",   "name": "Solana",             "asset_class": "crypto", "provider_id": "solana"},
    {"symbol": "DOGE",  "name": "Dogecoin",           "asset_class": "crypto", "provider_id": "dogecoin"},
    {"symbol": "ADA",   "name": "Cardano",            "asset_class": "crypto", "provider_id": "cardano"},
    {"symbol": "XRP",   "name": "XRP",                "asset_class": "crypto", "provider_id": "ripple"},
    {"symbol": "LTC",   "name": "Litecoin",           "asset_class": "crypto", "provider_id": "litecoin"},
    {"symbol": "DOT",   "name": "Polkadot",           "asset_class": "crypto", "provider_id": "polkadot"},

    # FIAT currencies, priced in USD (Frankfurter / ECB)
    {"symbol": "EUR",   "name": "Euro",               "asset_class": "fiat",   "provider_id": "EUR"},
    {"symbol": "GBP",   "name": "British Pound",      "asset_class": "fiat",   "provider_id": "GBP"},
    {"symbol": "JPY",   "name": "Japanese Yen",       "asset_class": "fiat",   "provider_id": "JPY"},
    {"symbol": "CAD",   "name": "Canadian Dollar",    "asset_class": "fiat",   "provider_id": "CAD"},
    {"symbol": "AUD",   "name": "Australian Dollar",  "asset_class": "fiat",   "provider_id": "AUD"},
    {"symbol": "CHF",   "name": "Swiss Franc",        "asset_class": "fiat",   "provider_id": "CHF"},
    {"symbol": "CNY",   "name": "Chinese Yuan",       "asset_class": "fiat",   "provider_id": "CNY"},
    {"symbol": "INR",   "name": "Indian Rupee",       "asset_class": "fiat",   "provider_id": "INR"},
]

# --- Lookup helpers ----------------------------------------------------------
ASSET_BY_SYMBOL = {a["symbol"]: a for a in ASSETS}


def get_asset(symbol):
    """Return the asset config dict for a display symbol, or None."""
    return ASSET_BY_SYMBOL.get(symbol)


def symbols():
    """All tradable display symbols."""
    return [a["symbol"] for a in ASSETS]


def symbols_by_class(asset_class):
    """Display symbols filtered to one asset class."""
    return [a["symbol"] for a in ASSETS if a["asset_class"] == asset_class]
