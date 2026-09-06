#!/usr/bin/env bash
# Start the dashboard locally. Binds to localhost only.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -r requirements.txt
echo "Dashboard on http://localhost:${PORT:-8000}"
exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" "$@"
