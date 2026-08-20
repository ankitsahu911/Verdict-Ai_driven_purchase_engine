"""
Test PostgreSQL connectivity via SQLAlchemy.

Prerequisites:
  - Docker container running (docker compose up -d)
  - DATABASE_URL set in .env (or uses default localhost:5432/verdict)
"""

import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so `app.db` can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

from app.db import DATABASE_URL  # noqa: E402  — needs dotenv loaded first

# ---------------------------------------------------------------------------
# 1. Connect
# ---------------------------------------------------------------------------
print(f"Connecting to: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Quick ping
    result = conn.execute(text("SELECT 1"))
    assert result.scalar() == 1, "Basic query failed"
    print("  Connection OK  (SELECT 1 returned 1)")

# ---------------------------------------------------------------------------
# 2. Create a throwaway table, insert, select, drop
# ---------------------------------------------------------------------------
TABLE_NAME = "_verdict_test_throwaway"

print(f"Creating table `{TABLE_NAME}` …")

with engine.begin() as conn:
    conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))
    conn.execute(
        text(f"""
        CREATE TABLE {TABLE_NAME} (
            id   INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL
        )
    """)
    )
    conn.execute(
        text(f"INSERT INTO {TABLE_NAME} (id, name) VALUES (1, 'verdict-test')")
    )

with engine.connect() as conn:
    rows = conn.execute(text(f"SELECT id, name FROM {TABLE_NAME}")).fetchall()
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    row = rows[0]
    print(f"  Read back: id={row[0]}, name={row[1]!r}")

with engine.begin() as conn:
    conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))

print("\nPostgreSQL test PASSED")
