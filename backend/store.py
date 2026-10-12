"""Small SQLite store for durable local download state."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4


class DownloadStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS playlists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS playlist_items (
                    id TEXT PRIMARY KEY,
                    playlist_id TEXT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS playlist_items_list ON playlist_items(playlist_id);
                """
            )

    @staticmethod
    def _playlist(connection, playlist_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT id, name, created_at FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
        if row is None:
            return None
        playlist = dict(row)
        playlist["items"] = [json.loads(item["payload"]) for item in connection.execute(
            "SELECT payload FROM playlist_items WHERE playlist_id = ? ORDER BY rowid", (playlist_id,)
        )]
        return playlist

    def list_playlists(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            ids = [row[0] for row in connection.execute("SELECT id FROM playlists ORDER BY rowid")]
            return [self._playlist(connection, playlist_id) for playlist_id in ids]

    @staticmethod
    def _insert_playlist_item(connection, playlist_id: str, item: dict[str, Any]) -> dict[str, Any]:
        saved = {"id": str(uuid4()), **item}
        connection.execute("INSERT INTO playlist_items(id, playlist_id, url, payload) VALUES (?, ?, ?, ?)",
                           (saved["id"], playlist_id, saved["url"], json.dumps(saved, ensure_ascii=False)))
        return saved

    def create_playlist(self, name: str, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        playlist_id = str(uuid4())
        with self._connect() as connection:
            connection.execute("INSERT INTO playlists(id, name) VALUES (?, ?)", (playlist_id, name))
            for item in items or []:
                self._insert_playlist_item(connection, playlist_id, item)
            return self._playlist(connection, playlist_id)

    def rename_playlist(self, playlist_id: str, name: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id))
            return self._playlist(connection, playlist_id)

    def delete_playlist(self, playlist_id: str) -> bool:
        with self._connect() as connection:
            return connection.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,)).rowcount > 0

    def add_playlist_item(self, playlist_id: str, item: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as connection:
            # Serialize duplicate detection and insertion across concurrent requests.
            connection.execute("BEGIN IMMEDIATE")
            if not connection.execute("SELECT 1 FROM playlists WHERE id = ?", (playlist_id,)).fetchone():
                return None
            duplicate = connection.execute("SELECT 1 FROM playlist_items WHERE playlist_id = ? AND url = ?",
                                           (playlist_id, item["url"])).fetchone() is not None
            return {**self._insert_playlist_item(connection, playlist_id, item), "duplicate": duplicate}

    def remove_playlist_item(self, playlist_id: str, item_id: str) -> bool:
        with self._connect() as connection:
            return connection.execute("DELETE FROM playlist_items WHERE playlist_id = ? AND id = ?",
                                      (playlist_id, item_id)).rowcount > 0

    def upsert(self, item: dict[str, Any]) -> None:
        payload = json.dumps(item, ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO downloads(id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (item["id"], payload),
            )

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM downloads WHERE id = ?", (task_id,)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM downloads ORDER BY updated_at DESC, rowid DESC"
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def delete(self, task_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM downloads WHERE id = ?", (task_id,))

    def replace_all(self, items: list[dict[str, Any]]) -> None:
        payloads = [(item["id"], json.dumps(item, ensure_ascii=False)) for item in items]
        ids = {task_id for task_id, _ in payloads}
        if len(ids) != len(payloads):
            raise sqlite3.IntegrityError("Duplicate download IDs in history snapshot")
        with self._connect() as connection:
            existing = dict(connection.execute("SELECT id, payload FROM downloads"))
            connection.executemany(
                "DELETE FROM downloads WHERE id = ?",
                [(task_id,) for task_id in existing if task_id not in ids],
            )
            connection.executemany(
                """
                INSERT INTO downloads(id, payload) VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                [(task_id, payload) for task_id, payload in payloads
                 if existing.get(task_id) != payload],
            )

    def migrate_json(self, legacy_path: str | Path) -> int:
        legacy = Path(legacy_path)
        with self._connect() as connection:
            marker = connection.execute(
                "SELECT value FROM metadata WHERE key = 'history_json_migrated'"
            ).fetchone()
        if marker or not legacy.exists():
            return 0

        raw = json.loads(legacy.read_text(encoding="utf-8"))
        values = raw.values() if isinstance(raw, dict) else raw
        count = 0
        for item in values:
            value = dict(item)
            value["status"] = {"done": "completed", "error": "failed"}.get(
                value.get("status"), value.get("status", "failed")
            )
            value.setdefault("progress", 100 if value["status"] == "completed" else 0)
            self.upsert(value)
            count += 1
        shutil.copy2(legacy, legacy.with_suffix(legacy.suffix + ".bak"))
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('history_json_migrated', '1')"
            )
        return count
