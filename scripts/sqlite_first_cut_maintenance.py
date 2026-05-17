"""One-shot SQLite maintenance after removing duplicate lifecycle index.

Default mode is dry-run. Use --apply only after the Flask app and import jobs are
stopped, because VACUUM needs exclusive access and rewrites the database file.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def format_size(num_bytes: int) -> str:
    mib = num_bytes / 1024 / 1024
    return f"{mib:.2f} MiB"


def index_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def run_maintenance(db_path: Path, backup_dir: Path, apply: bool) -> int:
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 2

    before_size = db_path.stat().st_size
    print(f"Database: {db_path}")
    print(f"Initial size: {format_size(before_size)}")

    conn = sqlite3.connect(str(db_path))
    try:
        legacy_present = index_exists(conn, "idx_sn_check_hist_open")
        lifecycle_present = index_exists(conn, "idx_sn_lifecycle_open_point")
        print(f"idx_sn_check_hist_open present: {legacy_present}")
        print(f"idx_sn_lifecycle_open_point present: {lifecycle_present}")

        if not apply:
            print("Dry run only. Re-run with --apply to backup, checkpoint, vacuum, and integrity-check.")
            return 0

        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"{db_path.name}.{stamp}.bak"
        conn.close()
        shutil.copy2(db_path, backup_path)
        print(f"Backup: {backup_path}")

        conn = sqlite3.connect(str(db_path))
        conn.execute("DROP INDEX IF EXISTS idx_sn_check_hist_open")
        conn.commit()

        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        print(f"WAL checkpoint: {checkpoint}")

        conn.execute("VACUUM")

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"Integrity check: {integrity}")
        if integrity != "ok":
            print("Integrity check failed. Restore the backup before continuing.")
            return 1
    finally:
        conn.close()

    after_size = db_path.stat().st_size
    print(f"Final size: {format_size(after_size)}")
    print(f"Saved: {format_size(before_size - after_size)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=str(Path("db") / "report.db"),
        help="Path to the runtime SQLite database.",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(Path("db") / "backups"),
        help="Directory for timestamped database backups.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform backup, index drop, WAL checkpoint, VACUUM, and integrity check.",
    )
    args = parser.parse_args()

    return run_maintenance(
        db_path=Path(args.db),
        backup_dir=Path(args.backup_dir),
        apply=args.apply,
    )


if __name__ == "__main__":
    raise SystemExit(main())
