import sqlite3
from datetime import date

from src.models import Notice
from src.store import SCHEMA, Store


def make_notice(content_hash: str = "abc123") -> Notice:
    return Notice(
        id="LH:1",
        source="LH",
        source_notice_id="1",
        title="테스트 공고",
        content_hash=content_hash,
    )


def test_upsert_new_then_unchanged(tmp_path):
    store = Store(tmp_path / "notices.db")
    try:
        assert store.upsert(make_notice()) == "new"
        assert store.upsert(make_notice()) == "unchanged"
    finally:
        store.close()


def test_upsert_changed_keeps_first_seen_at(tmp_path):
    store = Store(tmp_path / "notices.db")
    try:
        store.upsert(make_notice(content_hash="hash-v1"))
        first_seen = store.get("LH:1").first_seen_at

        assert store.upsert(make_notice(content_hash="hash-v2")) == "changed"
        updated = store.get("LH:1")
        assert updated.content_hash == "hash-v2"
        assert updated.first_seen_at == first_seen
    finally:
        store.close()


def test_get_missing_returns_none(tmp_path):
    store = Store(tmp_path / "notices.db")
    try:
        assert store.get("SH:없음") is None
    finally:
        store.close()


def test_set_review_dates(tmp_path):
    store = Store(tmp_path / "notices.db")
    try:
        store.upsert(make_notice())
        store.set_review_dates("LH:1", date(2026, 10, 23), date(2026, 12, 28))
        notice = store.get("LH:1")
        assert notice.doc_review_date.isoformat() == "2026-10-23"
        assert notice.result_date.isoformat() == "2026-12-28"
    finally:
        store.close()


def test_migrates_old_schema_without_review_date_columns(tmp_path):
    """배포된 옛날 DB엔 doc_review_date/result_date 컬럼이 없다 — Store가 열 때
    자동으로 추가해줘야(마이그레이션) 기존 DB를 그대로 이어서 쓸 수 있다."""
    db_path = tmp_path / "old.db"
    old_schema = SCHEMA.split("doc_review_date TEXT,\n    result_date TEXT,\n")[0] + SCHEMA.split(
        "result_date TEXT,\n"
    )[1]
    conn = sqlite3.connect(db_path)
    conn.executescript(old_schema)
    conn.commit()
    conn.close()

    store = Store(db_path)  # 여기서 마이그레이션 발생
    try:
        store.upsert(make_notice())
        assert store.get("LH:1").doc_review_date is None  # 에러 없이 조회되면 성공
    finally:
        store.close()
