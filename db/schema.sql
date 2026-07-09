-- Trading game schema. All monetary values are USD.
-- Safe to run repeatedly; every statement is IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS players (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    cash          REAL    NOT NULL,
    created_at    INTEGER NOT NULL,
    password_hash TEXT,                  -- PBKDF2 string, null only for legacy rows
    recovery_hash TEXT                   -- PBKDF2 hash of the normalized memorable word
);

-- Session tokens issued on login/register/recover. A player may have several
-- (e.g. phone + laptop); logout deletes one, a password reset can clear them all.
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    player_id  INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS holdings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    symbol    TEXT    NOT NULL,
    quantity  REAL    NOT NULL,          -- units held (may be fractional)
    avg_cost  REAL    NOT NULL,          -- average USD cost basis per unit
    UNIQUE(player_id, symbol),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    symbol    TEXT    NOT NULL,
    side      TEXT    NOT NULL,          -- 'buy' or 'sell'
    quantity  REAL    NOT NULL,
    price     REAL    NOT NULL,          -- USD per unit at execution
    total     REAL    NOT NULL,          -- USD value of the trade
    ts        INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Optional persistent price cache the market layer may use to survive restarts
-- and to fall back on when a provider is unreachable.
CREATE TABLE IF NOT EXISTS price_cache (
    symbol     TEXT PRIMARY KEY,
    price      REAL NOT NULL,            -- USD
    prev_close REAL,                     -- USD, for daily change %
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_assets (
    symbol      TEXT PRIMARY KEY,
    name        TEXT    NOT NULL,
    asset_class TEXT    NOT NULL,       -- 'stock' | 'crypto' | 'fiat'
    provider_id TEXT    NOT NULL,
    added_by    INTEGER,                -- player id, nullable
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_holdings_player ON holdings(player_id);
CREATE INDEX IF NOT EXISTS idx_tx_player       ON transactions(player_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_player ON sessions(player_id);
