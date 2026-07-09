# Trading game

Trading game is a local, browser-based paper-trading game for a few people on the same network. Everyone gets play money, then buys and sells real-world stocks, cryptocurrencies, and currencies at live USD prices. It is for fun and learning, not financial advice. The prices are real, but every trade is fake. The login is a friendly barrier so players do not trample each other's portfolios; do not reuse a real password here.

## Features

- Local multiplayer accounts with a username, password, and memorable recovery word. No email.
- 100,000 virtual dollars for each new player by default.
- Live prices for stocks, crypto, and fiat currencies priced in USD.
- Portfolio totals with current value, cost basis, profit/loss, and price-history charts.
- Transaction history and a local leaderboard.
- Player-added stocks, crypto, and currencies that become tradable for everyone.
- FastAPI and SQLite on the backend, plain HTML/CSS/JS on the frontend, with Chart.js vendored in `web/vendor/`.
- Keyless market data. No API keys or signups needed.

## Quick start with Docker

Docker is the easiest way to run the game:

```bash
docker compose up --build
```

After the first build, this is usually enough:

```bash
docker compose up
```

Open `http://localhost:8000` on the machine running Docker. From a phone, tablet, or another computer on the same home network, open `http://<your-machine-ip>:8000`.

The SQLite database lives in a named Docker volume, so accounts and trades survive restarts. It is not written into the repository and should never be committed.

## Quick start without Docker

You need Python 3.10 or newer. From the project root, run:

```bash
./run.sh
```

The script creates `.venv/` if needed, installs the Python dependencies, and starts the FastAPI server on port 8000. Open `http://localhost:8000` in your browser. Use `http://<your-machine-ip>:8000` from other devices on the same network.

Press Ctrl-C in the terminal to stop the server.

## How to play

Create an account with a trader name, a password, and a memorable word for password recovery. Each new account starts with 100,000 virtual dollars unless the host changes the starting balance.

Browse the market, place buy or sell orders at the current live price, then watch your portfolio and the leaderboard. Crypto and fiat trades can be fractional, so you can buy 0.01 BTC or a slice of a currency position instead of a whole unit.

## Adding your own assets

Any signed-in player can add an asset if it is not already in the game. Stocks are added by ticker, crypto is found through CoinGecko search and added with the chosen coin, and fiat currencies are added by ISO code such as `SEK` or `NZD`.

The app checks that the asset can actually be priced before saving it. Once added, it appears in the shared market and everyone can trade it.

## Configuration

All settings are optional. For Docker, copy `.env.example` to `.env` and edit the values you want to change.

| Variable | Default | What it controls |
|---|---:|---|
| `TRADING_GAME_DB` | `trading_game.db` | SQLite database path. In Docker this is normally inside a named volume. |
| `TRADING_GAME_HOST` | `0.0.0.0` | Host/interface the app binds to. |
| `TRADING_GAME_PORT` | `8000` | HTTP port. |
| `TRADING_GAME_STARTING_CASH` | `100000` | Virtual dollars given to each new player. |
| `TRADING_GAME_CACHE_TTL` | `60` | Seconds before a fetched price is considered stale. |

## Data and privacy

Data stays local. By default, accounts, holdings, sessions, transactions, cached prices, and custom assets live in `trading_game.db`; with Docker, they live in the configured volume. The database is ignored by git and should not be shared or committed.

There is no telemetry, no email, and no hosted service behind the app. Passwords and memorable words are hashed in the database, but this is still a home-network game rather than a security product.

## How it works

The backend is FastAPI with a small SQLite database. It serves the static frontend from `web/` and exposes JSON endpoints under `/api`; see `API_CONTRACT.md` for the full contract.

Market data comes from keyless providers: Yahoo Finance for stocks, CoinGecko for crypto, and Frankfurter/ECB for fiat currencies. The market layer normalizes prices to USD and caches them for about 60 seconds so the app is usable without hammering the free endpoints.

The frontend is plain HTML, CSS, and JavaScript. There is no build step. Chart.js is vendored so the charts work without pulling a package during startup.

## Data sources and their quirks

Real markets do not all move at the same time. Stocks and fiat pairs are livelier during their normal trading windows, while crypto keeps moving through weekends.

The free endpoints are convenient, but they are not guaranteed. Yahoo's stock endpoints are unofficial and can rate-limit. The app caches prices and falls back to the last known value when a provider has a short outage, so a blip should not stop the game.

## Development and testing

Run commands from the project root so `import config` resolves correctly. For local development, start the server with `./run.sh` or Docker.

An end-to-end smoke test lives at `scripts/smoke_test.py`. Run it against a running server with the virtualenv Python:

```bash
./.venv/bin/python scripts/smoke_test.py
```

There is also `scripts/custom_assets_test.py`, which exercises the add-your-own-asset flow the same way.

Keep that smoke test passing when you change the backend, frontend, or schema.

## Roadmap

Ideas for making the game feel more like real trading, from conditional orders and
trading fees to market hours, dividends, and short selling, live in `ROADMAP.md`.

## License

MIT. See `LICENSE`.
