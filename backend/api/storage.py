"""
Where the app keeps its data: a SQLite database plus folders of files.

Everything lives under backend/storage/ (which .gitignore keeps out of GitHub).
"""

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent / "storage"
ROM_FOLDER = STORAGE / "roms"
DATABASE = STORAGE / "chip8rl.db"


def connect():
    """Open the database, creating the folders and tables the first time."""
    ROM_FOLDER.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row                 # rows behave like dictionaries
    db.execute("""
        CREATE TABLE IF NOT EXISTS roms (
            id        TEXT PRIMARY KEY,          -- fingerprint (hash) of the ROM's bytes
            name      TEXT NOT NULL,
            size      INTEGER NOT NULL,
            added_at  TEXT NOT NULL
        )
    """)
    return db


def rom_id_for(data):
    """A short fingerprint of the ROM's contents - the same game always gets the same id."""
    return hashlib.sha256(data).hexdigest()[:16]


def add_rom(name, data):
    """Save a ROM (if it isn't already stored) and return its record."""
    rom_id = rom_id_for(data)
    with connect() as db:
        existing = db.execute("SELECT * FROM roms WHERE id = ?", (rom_id,)).fetchone()
        if existing:
            return dict(existing)
        (ROM_FOLDER / f"{rom_id}.ch8").write_bytes(data)
        record = {"id": rom_id, "name": name, "size": len(data),
                  "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        db.execute("INSERT INTO roms VALUES (:id, :name, :size, :added_at)", record)
        return record


def list_roms():
    with connect() as db:
        rows = db.execute("SELECT * FROM roms ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


def get_rom(rom_id):
    """Return (record, bytes) for a stored ROM, or (None, None) if there's no such ROM."""
    with connect() as db:
        row = db.execute("SELECT * FROM roms WHERE id = ?", (rom_id,)).fetchone()
    if row is None:
        return None, None
    return dict(row), (ROM_FOLDER / f"{rom_id}.ch8").read_bytes()


def delete_rom(rom_id):
    with connect() as db:
        db.execute("DELETE FROM roms WHERE id = ?", (rom_id,))
    path = ROM_FOLDER / f"{rom_id}.ch8"
    if path.exists():
        path.unlink()
