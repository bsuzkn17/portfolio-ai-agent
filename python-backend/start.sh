#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PORT=${PORT:-8000}

if [ "${APP_ENV}" = "production" ]; then
    echo "[start] production mode — port $PORT"
    exec .venv/bin/python3 -m uvicorn main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --workers 2
else
    echo "[start] development mode — port $PORT (hot-reload on)"
    exec .venv/bin/python3 -m uvicorn main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --reload
fi
