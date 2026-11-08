"""SQLite storage for checklists and their items."""
from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone

from .extractor import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS checklists (
    id INTEGER PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    msg_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    sender TEXT,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
    pos INTEGER NOT NULL,
    text TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def exists(self, msg_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM checklists WHERE msg_id=?", (msg_id,)).fetchone() is not None

    def create(self, msg_id: str, title: str, sender: str, items: list[Item]) -> str:
        token = secrets.token_urlsafe(12)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO checklists(token, msg_id, title, sender, created) VALUES (?,?,?,?,?)",
                (token, msg_id, title, sender, datetime.now(timezone.utc).isoformat()),
            )
            self.db.executemany(
                "INSERT INTO items(list_id, pos, text) VALUES (?,?,?)",
                [(cur.lastrowid, i, it.label()) for i, it in enumerate(items)],
            )
        return token

    def get(self, token: str):
        lst = self.db.execute("SELECT * FROM checklists WHERE token=?", (token,)).fetchone()
        if lst is None:
            return None, []
        items = self.db.execute("SELECT * FROM items WHERE list_id=? ORDER BY pos", (lst["id"],)).fetchall()
        return lst, items

    def toggle(self, token: str, item_id: int) -> bool | None:
        with self.db:
            row = self.db.execute(
                "SELECT i.id, i.done FROM items i JOIN checklists c ON c.id=i.list_id "
                "WHERE c.token=? AND i.id=?",
                (token, item_id),
            ).fetchone()
            if row is None:
                return None
            new = 0 if row["done"] else 1
            self.db.execute("UPDATE items SET done=? WHERE id=?", (new, item_id))
            return bool(new)

    def recent(self, limit: int = 50):
        return self.db.execute(
            "SELECT c.*, COUNT(i.id) total, COALESCE(SUM(i.done),0) done FROM checklists c "
            "LEFT JOIN items i ON i.list_id=c.id GROUP BY c.id ORDER BY c.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
