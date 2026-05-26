#!/bin/sh
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
