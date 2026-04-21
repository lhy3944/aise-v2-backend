"""Bootstrap the pytest database (aise_test) and apply Alembic migrations.

Team policy: pytest does NOT auto-create databases. Run this once per fresh
environment (or after dropping the test DB). It is idempotent.

Environment variables (all optional; defaults match local dev compose):
    TEST_DB_NAME      default: aise_test
    TEST_DB_USER      default: aise
    TEST_DB_PASSWORD  default: aise1234
    TEST_DB_HOST      default: localhost
    TEST_DB_PORT      default: 5432

Usage:
    cd backend && uv run python scripts/setup_test_db.py
    # or via the shell wrapper:
    cd backend && bash scripts/setup_test_db.sh
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def ensure_database() -> tuple[str, str]:
    name = _env("TEST_DB_NAME", "aise_test")
    user = _env("TEST_DB_USER", "aise")
    password = _env("TEST_DB_PASSWORD", "aise1234")
    host = _env("TEST_DB_HOST", "localhost")
    port = _env("TEST_DB_PORT", "5432")

    admin_conn = psycopg2.connect(
        dbname="postgres", user=user, password=password, host=host, port=port
    )
    admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with admin_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            if cur.fetchone():
                print(f"    '{name}' already exists, skipping CREATE DATABASE.")
            else:
                print(f"    Creating database '{name}'...")
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(name), sql.Identifier(user)
                    )
                )
    finally:
        admin_conn.close()

    async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
    return name, async_url


def run_migrations(async_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = async_url
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"alembic upgrade head failed (exit {result.returncode})")


def main() -> None:
    print("==> Checking test database...")
    name, async_url = ensure_database()
    print(f"==> Running alembic upgrade head against '{name}'...")
    run_migrations(async_url)
    print(f"==> Done. Test DB ready: {async_url}")


if __name__ == "__main__":
    main()
