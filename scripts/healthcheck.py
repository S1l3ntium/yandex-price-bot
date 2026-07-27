#!/usr/bin/env python3
"""Container healthcheck: validate env and SQLite accessibility without schema writes."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    db_path = Path(os.getenv("DATABASE_PATH", "data/prices.db")).expanduser()
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    uri = f"file:{db_path}?mode=rw"
    with sqlite3.connect(uri, uri=True, timeout=5) as conn:
        conn.execute("PRAGMA quick_check").fetchone()
        conn.execute("SELECT 1").fetchone()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
