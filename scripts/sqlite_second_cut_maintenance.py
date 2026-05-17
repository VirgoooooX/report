"""Apply second-cut SQLite index removals to the runtime database."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


DROP_INDEXES = (
    "idx_sn_lifecycle_current_progress",
    "idx_sn_lifecycle_current_failure",
    "idx_sn_check_hist_point",
)

KEEP_INDEXES = (
    "idx_sn_lifecycle_open_point",
    "idx_sn_lifecycle_sn",
    "idx_sn_lifecycle_window",
    "idx_sn_check_hist_failures",
)


def format_size(num_bytes: int) -> str:
    return f"{num_bytes / 1024 / 1024:.2f} MiB"


def index_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def backup_database(db_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{db_path.name}.second-cut.{stamp}.bak"
    source = sqlite3.connect(str(db_path))
    try:
        target = sqlite3.connect(str(backup_path))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return backup_path


def run(db_path: Path, backup_dir: Path, apply: bool) -> int:
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 2

    before_size = db_path.stat().st_size
    print(f"Database: {db_path}")
    print(f"Initial size: {format_size(before_size)}")

    conn = sqlite3.connect(str(db_path))
    try:
        for name in DROP_INDEXES + KEEP_INDEXES:
            print(f"{name} present: {index_exists(conn, name)}")
    finally:
        conn.close()

    if not apply:
        print("Dry run only. Re-run with --apply after stopping active writers.")
        return 0

    backup_path = backup_database(db_path, backup_dir)
    print(f"Backup: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        for name in DROP_INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        conn.commit()

        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        print(f"WAL checkpoint: {checkpoint}")

        conn.execute("VACUUM")

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"Integrity check: {integrity}")
        if integrity != "ok":
            print("Integrity check failed. Restore the backup before continuing.")
            return 1

        for name in DROP_INDEXES:
            if index_exists(conn, name):
                print(f"Drop failed; index still exists: {name}")
                return 1
        for name in KEEP_INDEXES:
            if not index_exists(conn, name):
                print(f"Required retained index missing: {name}")
                return 1
    finally:
        conn.close()

    after_size = db_path.stat().st_size
    print(f"Final size: {format_size(after_size)}")
    print(f"Saved: {format_size(before_size - after_size)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(Path("db") / "report.db"))
    parser.add_argument("--backup-dir", default=str(Path("db") / "backups"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    return run(Path(args.db), Path(args.backup_dir), args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
