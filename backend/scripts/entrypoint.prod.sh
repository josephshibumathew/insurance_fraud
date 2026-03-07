#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
fi

exec "$@"