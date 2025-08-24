#!/usr/bin/env bash
set -euo pipefail

echo "Entry point: checking for DATABASE_URL and running migrations"

DB_URL="${DATABASE_URL:-}"
WAIT_SECONDS=5
RETRIES=12

wait_for_db() {
  if [ -z "$DB_URL" ]; then
    echo "DATABASE_URL not set; skipping DB wait"
    return 0
  fi

  echo "Waiting for database to become available..."

  # Try using Python + SQLAlchemy if available (better semantics)
  python - <<PY || return 1
import os, time
db_url = os.environ.get('DATABASE_URL')
retries = int(os.environ.get('RETRIES', '12'))
wait = int(os.environ.get('WAIT_SECONDS', '5'))
if not db_url:
    print('No DATABASE_URL set; exiting wait')
    raise SystemExit(0)
try:
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    for i in range(retries):
        try:
            with engine.connect() as conn:
                print('Database reachable')
                break
        except Exception as e:
            print(f'Attempt {i+1}/{retries} failed: {e}')
            time.sleep(wait)
    else:
        raise SystemExit(2)
except Exception as e:
    # Fallback: try a simple TCP socket test by parsing host:port
    import socket
    from urllib.parse import urlparse
    u = urlparse(db_url)
    host = u.hostname or 'localhost'
    port = u.port or 5432
    for i in range(retries):
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.close()
            print('TCP connect succeeded')
            break
        except Exception as e2:
            print(f'TCP attempt {i+1}/{retries} failed: {e2}')
            time.sleep(wait)
    else:
        raise SystemExit(2)
PY
}

run_migrations() {
  if [ -f /app/alembic.ini ]; then
    echo "Running alembic upgrade head"
    alembic upgrade head
  else
    echo "alembic.ini not found, skipping migrations"
  fi
}

export RETRIES="$RETRIES"
export WAIT_SECONDS="$WAIT_SECONDS"

if wait_for_db; then
  run_migrations
else
  echo "Database did not become available after retries; exiting with error"
  exit 1
fi

# Execute passed command
exec "$@"
