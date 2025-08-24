#!/usr/bin/env bash
set -e

# Wait for database to be available (optional simple loop)
# You may replace with a more robust wait-for script if needed.
echo "Running database migrations..."
if [ -f /app/alembic.ini ]; then
  alembic upgrade head || echo "alembic command failed"
else
  echo "alembic.ini not found, skipping migrations"
fi

# Execute passed command
exec "$@"
