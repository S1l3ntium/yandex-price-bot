#!/usr/bin/env python3
"""Create a consistent SQLite backup using the SQLite Online Backup API."""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup yandex-price-bot SQLite database")
    parser.add_argument(
        "--source",
        default=None,
        help="Source SQLite DB path. Defaults to DATABASE_PATH or data/prices.db.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Backup directory. Defaults to BACKUP_DIR or backups/.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    source = Path(args.source or os.getenv("DATABASE_PATH", "data/prices.db")).expanduser()
    output_dir = Path(args.output_dir or os.getenv("BACKUP_DIR", "backups")).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        raise FileNotFoundError(f"Database file not found: {source}")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = output_dir / f"prices-{timestamp}.db"

    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
