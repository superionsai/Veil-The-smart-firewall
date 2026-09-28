from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from ..models import PrivacyRegion
from ..utils import sha256_text


class AuditStore:
    """Privacy-preserving audit log. Raw OCR text is off by default."""

    def __init__(self, path: Path, enabled: bool = True, retain_raw_text: bool = False):
        self.path = path
        self.enabled = enabled
        self.retain_raw_text = retain_raw_text
        self._lock = threading.RLock()
        if enabled:
            self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS privacy_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    text_hash TEXT,
                    raw_text TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON privacy_events(ts DESC)")
            conn.commit()

    def record(self, session_id: str, regions: list[PrivacyRegion]):
        if not self.enabled or not regions:
            return
        rows = []
        now = time.time()
        for region in regions:
            text = region.text or ""
            rows.append((
                now,
                session_id,
                region.category.value,
                region.action.value,
                region.source,
                float(region.confidence),
                sha256_text(text) if text else None,
                text if self.retain_raw_text and text else None,
            ))
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO privacy_events(ts,session_id,category,action,source,confidence,text_hash,raw_text) VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()

    def recent(self, limit: int = 50) -> list[dict]:
        if not self.enabled:
            return []
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT ts,session_id,category,action,source,confidence,text_hash,raw_text FROM privacy_events ORDER BY ts DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [dict(r) for r in rows]

    def aggregate(self) -> dict:
        if not self.enabled:
            return {"events": 0, "categories": {}}
        with self._lock, self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM privacy_events").fetchone()[0]
            cats = conn.execute("SELECT category,COUNT(*) n FROM privacy_events GROUP BY category ORDER BY n DESC").fetchall()
        return {"events": total, "categories": {r[0]: r[1] for r in cats}}

    def clear(self):
        if not self.enabled:
            return
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM privacy_events")
            conn.commit()
