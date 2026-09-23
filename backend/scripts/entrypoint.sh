#!/usr/bin/env sh
# Container start: migrate, optionally reset the sample data, then serve without auto-reload.
set -eu
echo "applying migrations"
alembic upgrade head
if [ "${SEED_ON_START:-1}" = "1" ]; then
  python -m scripts.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
