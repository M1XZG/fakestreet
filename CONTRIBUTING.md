# Contributing

Thanks for helping with Trading game. It is meant to stay small enough to run on a laptop and friendly enough that people can tinker with it without learning a build system first.

For local development, start from the project root. Use `./run.sh` if you want the Python path: it creates `.venv/`, installs `requirements.txt`, and starts the server. If the Docker files are present, `docker compose up --build` gives you the same app with the database kept in a Docker volume.

The main pieces are easy to find. `config.py` holds the built-in asset universe and shared settings. `app/` is the FastAPI backend, including auth, game rules, database access, and market-data providers. `web/` is the plain HTML/CSS/JS frontend. `db/schema.sql` is the SQLite schema, and `API_CONTRACT.md` is the API the frontend and backend agree on.

Pull requests should keep the game simple. Prefer clear code over clever code, update the README or API contract when behaviour changes, and avoid adding services, build steps, or API keys unless there is a strong reason.

Before opening a PR, run the app and make sure the smoke test still passes once `scripts/smoke_test.py` is available:

```bash
./.venv/bin/python scripts/smoke_test.py
```
