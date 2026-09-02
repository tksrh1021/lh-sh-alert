"""SQLite 저장소. content_hash로 신규/변경/동일을 구분한다."""
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path

from src.models import Notice

SCHEMA = """
CREATE TABLE IF NOT EXISTS notices (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_notice_id TEXT NOT NULL,
    title TEXT NOT NULL,
    housing_type TEXT,
    target_groups TEXT NOT NULL,
    regions TEXT NOT NULL,
    posted_at TEXT,
    apply_start TEXT,
    apply_end TEXT,
    detail_url TEXT,
    pdf_urls TEXT NOT NULL,
    raw TEXT NOT NULL,
    conditions TEXT,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    notice_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    PRIMARY KEY (notice_id, kind)
);
"""


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _row_to_notice(row: sqlite3.Row) -> Notice:
    return Notice(
        id=row["id"],
        source=row["source"],
        source_notice_id=row["source_notice_id"],
        title=row["title"],
        housing_type=row["housing_type"],
        target_groups=json.loads(row["target_groups"]),
        regions=json.loads(row["regions"]),
        posted_at=row["posted_at"],
        apply_start=row["apply_start"],
        apply_end=row["apply_end"],
        detail_url=row["detail_url"],
        pdf_urls=json.loads(row["pdf_urls"]),
        raw=json.loads(row["raw"]),
        conditions=json.loads(row["conditions"]) if row["conditions"] else None,
        first_seen_at=row["first_seen_at"],
        updated_at=row["updated_at"],
        content_hash=row["content_hash"],
    )


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get(self, notice_id: str) -> Notice | None:
        row = self.conn.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
        return _row_to_notice(row) if row else None

    def all(self) -> list[Notice]:
        rows = self.conn.execute("SELECT * FROM notices ORDER BY source, id").fetchall()
        return [_row_to_notice(r) for r in rows]

    def has_notified(self, notice_id: str, kind: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM notifications WHERE notice_id = ? AND kind = ?", (notice_id, kind)
        ).fetchone()
        return row is not None

    def set_conditions(self, notice_id: str, conditions: dict) -> None:
        self.conn.execute(
            "UPDATE notices SET conditions = ? WHERE id = ?", (_dumps(conditions), notice_id)
        )
        self.conn.commit()

    def record_notification(self, notice_id: str, kind: str, channel: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO notifications (notice_id, kind, sent_at, channel) VALUES (?, ?, ?, ?)",
            (notice_id, kind, datetime.now().isoformat(), channel),
        )
        self.conn.commit()

    def upsert(self, notice: Notice) -> str:
        """반환값: 'new' / 'changed' / 'unchanged'"""
        existing = self.conn.execute(
            "SELECT content_hash, first_seen_at FROM notices WHERE id = ?", (notice.id,)
        ).fetchone()
        now = datetime.now().isoformat()

        if existing is None:
            notice.first_seen_at = now
            notice.updated_at = now
            self._insert(notice)
            return "new"

        if existing["content_hash"] == notice.content_hash:
            return "unchanged"

        notice.first_seen_at = existing["first_seen_at"]
        notice.updated_at = now
        self._insert(notice, replace=True)
        return "changed"

    def _insert(self, notice: Notice, replace: bool = False) -> None:
        verb = "INSERT OR REPLACE" if replace else "INSERT"
        self.conn.execute(
            f"""{verb} INTO notices (
                id, source, source_notice_id, title, housing_type, target_groups,
                regions, posted_at, apply_start, apply_end, detail_url, pdf_urls,
                raw, conditions, first_seen_at, updated_at, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                notice.id,
                notice.source,
                notice.source_notice_id,
                notice.title,
                notice.housing_type,
                _dumps(notice.target_groups),
                _dumps(notice.regions),
                notice.posted_at.isoformat() if isinstance(notice.posted_at, date) else notice.posted_at,
                notice.apply_start.isoformat() if isinstance(notice.apply_start, date) else notice.apply_start,
                notice.apply_end.isoformat() if isinstance(notice.apply_end, date) else notice.apply_end,
                notice.detail_url,
                _dumps(notice.pdf_urls),
                _dumps(notice.raw),
                _dumps(notice.conditions) if notice.conditions else None,
                notice.first_seen_at,
                notice.updated_at,
                notice.content_hash,
            ),
        )
        self.conn.commit()
