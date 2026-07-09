#!/usr/bin/env bash
# Launch the trading game on the local network.
# Run from anywhere; this cd's to the project root so imports resolve.
set -euo pipefail

cd "$(dirname "$0")"

# Create a virtualenv on first run and install deps.
if [ ! -d ".venv" ]; then
    echo "First run: creating virtualenv and installing requirements..."
    python3 -m venv .venv
    ./.venv/bin/pip install --quiet --upgrade pip
    ./.venv/bin/pip install --quiet -r requirements.txt
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "Starting trading game on http://${HOST}:${PORT}  (Ctrl-C to stop)"
echo "On the local network, open http://<this-machine-ip>:${PORT}"
exec ./.venv/bin/python -m uvicorn app.main:app --host "$HOST" --port "$PORT"
