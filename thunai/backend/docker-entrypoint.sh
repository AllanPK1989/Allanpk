#!/bin/sh
# Apply database migrations, seed SAMPLE data on an empty database (if SEED_SAMPLE_DATA=true),
# then start the API.
set -e
alembic upgrade head
python -m app.cli init
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips='*' --workers "${WEB_WORKERS:-2}"
