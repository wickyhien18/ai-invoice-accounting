#!/bin/sh
# Khoi dong backend tren host deploy: tao/cap nhat bang, nap du lieu demo (neu bat), roi chay API.
set -e
alembic upgrade head
if [ "$SEED_DEMO" = "1" ]; then python scripts/seed_if_empty.py; fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
