#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for postgres..."
python - <<'PY'
import asyncio
import os
import sys
import asyncpg

async def main():
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://legal_bot:legal_bot_pass@postgres:5432/legal_chatbot")
    pg_url = url.replace("postgresql+asyncpg://", "postgresql://")
    last = None
    for _ in range(60):
        try:
            conn = await asyncpg.connect(pg_url)
            await conn.close()
            return
        except Exception as exc:
            last = exc
            await asyncio.sleep(2)
    print(f"postgres not ready: {last}", file=sys.stderr)
    raise SystemExit(1)

asyncio.run(main())
PY

echo "Running Alembic migrations..."
alembic -c shared/alembic.ini upgrade head

exec "$@"
