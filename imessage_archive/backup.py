"""Locate and read files inside a local iPhone (Finder/iTunes) backup.

A local backup stores every file under a hashed name (its fileID), sharded
into 2-character subfolders. The only way to find a real file (like
Library/SMS/sms.db) is via Manifest.db, which maps (domain, relativePath)
pairs to fileIDs. Everything here is read-only — the backup is never
modified.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

SMS_DOMAIN = "HomeDomain"
SMS_RELATIVE_PATH = "Library/SMS/sms.db"


def open_manifest(backup_path: Path) -> sqlite3.Connection:
    """Open Manifest.db from the backup folder, read-only."""
    manifest_path = backup_path / "Manifest.db"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"No Manifest.db found in {backup_path} — is this a valid, "
            "unencrypted local backup folder?"
        )
    return sqlite3.connect(f"file:{manifest_path}?mode=ro", uri=True)


def resolve_file(
    manifest_conn: sqlite3.Connection,
    backup_path: Path,
    domain: str,
    relative_path: str,
) -> Path:
    """Look up a (domain, relativePath) pair and return its real on-disk path."""
    row = manifest_conn.execute(
        "SELECT fileID FROM Files WHERE domain = ? AND relativePath = ?",
        (domain, relative_path),
    ).fetchone()
    if row is None:
        raise FileNotFoundError(
            f"{domain}:{relative_path} not found in backup "
            "(no matching entry in Manifest.db)"
        )
    file_id = row[0]
    real_path = backup_path / file_id[:2] / file_id
    if not real_path.is_file():
        raise FileNotFoundError(
            f"Manifest.db points {domain}:{relative_path} to {real_path}, "
            "but that file isn't there"
        )
    return real_path


def extract_chat_db(backup_path: Path, dest_dir: Path) -> Path:
    """Copy sms.db (+ -wal/-shm if present) out of the backup into dest_dir.

    Copying the -wal/-shm files alongside sms.db matters: SQLite may not have
    checkpointed recent writes into sms.db itself yet, so without them the
    most recent messages could be missing. SQLite merges the WAL
    automatically the next time sms.db is opened normally.

    Returns the path to the copied sms.db.
    """
    backup_path = Path(backup_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    conn = open_manifest(backup_path)
    try:
        dest_db = None
        for suffix in ("", "-wal", "-shm"):
            relative_path = f"{SMS_RELATIVE_PATH}{suffix}"
            try:
                src = resolve_file(conn, backup_path, SMS_DOMAIN, relative_path)
            except FileNotFoundError:
                if suffix == "":
                    raise
                continue  # -wal / -shm are optional
            dest = dest_dir / f"chat.db{suffix}"
            shutil.copy2(src, dest)
            if suffix == "":
                dest_db = dest
        return dest_db
    finally:
        conn.close()
