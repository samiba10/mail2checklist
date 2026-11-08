"""SQLite storage for checklists and their items."""
from __future__ import annotations

import json
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
    detail TEXT NOT NULL DEFAULT '',
    phones TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint TEXT PRIMARY KEY,
    sub_json TEXT NOT NULL,
    created TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")   # web + poller share the file
        self.db.execute("PRAGMA busy_timeout = 5000")
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
                "INSERT INTO items(list_id, pos, text, detail, phones) VALUES (?,?,?,?,?)",
                [
                    (cur.lastrowid, i, f"{it.qty} × {it.name}" if it.qty else it.name, it.note, ",".join(it.phones))
                    for i, it in enumerate(items)
                ],
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

    # --- web push subscriptions (one per installed device) ---
    def add_push_subscription(self, sub: dict) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO push_subs(endpoint, sub_json, created) VALUES (?,?,?) "
                "ON CONFLICT(endpoint) DO UPDATE SET sub_json=excluded.sub_json",
                (sub["endpoint"], json.dumps(sub), datetime.now(timezone.utc).isoformat()),
            )

    def remove_push_subscription(self, endpoint: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))

    def push_subscriptions(self) -> list[tuple[str, dict]]:
        return [(r["endpoint"], json.loads(r["sub_json"])) for r in self.db.execute("SELECT * FROM push_subs")]

    def recent(self, limit: int = 50):
        return self.db.execute(
            "SELECT c.*, COUNT(i.id) total, COALESCE(SUM(i.done),0) done FROM checklists c "
            "LEFT JOIN items i ON i.list_id=c.id GROUP BY c.id ORDER BY c.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
