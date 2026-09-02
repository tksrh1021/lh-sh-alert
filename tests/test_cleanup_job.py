from datetime import date

from src.jobs import cleanup as cleanup_job
from src.models import Notice
from src.store import Store


def make_notice(id_, apply_end=None) -> Notice:
    return Notice(
        id=f"LH:{id_}", source="LH", source_notice_id=id_, title=f"공고 {id_}",
        apply_end=apply_end, content_hash=id_,
    )


def test_deletes_only_confirmed_expired_notices(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice("expired", apply_end=date(2026, 1, 1)))
    store.upsert(make_notice("still_open", apply_end=date(2099, 1, 1)))
    store.upsert(make_notice("unknown", apply_end=None))
    store.close()

    monkeypatch.setattr(cleanup_job, "DB_PATH", db_path)
    expired = cleanup_job.run(today=date(2026, 6, 1))

    assert [n.id for n in expired] == ["LH:expired"]

    store = Store(db_path)
    try:
        assert store.get("LH:expired") is None
        assert store.get("LH:still_open") is not None
        assert store.get("LH:unknown") is not None
    finally:
        store.close()


def test_dry_run_does_not_delete(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice("expired", apply_end=date(2026, 1, 1)))
    store.close()

    monkeypatch.setattr(cleanup_job, "DB_PATH", db_path)
    cleanup_job.run(today=date(2026, 6, 1), dry_run=True)

    store = Store(db_path)
    try:
        assert store.get("LH:expired") is not None
    finally:
        store.close()


def test_delete_also_removes_notification_history(tmp_path):
    store = Store(tmp_path / "notices.db")
    try:
        store.upsert(make_notice("x", apply_end=date(2026, 1, 1)))
        store.record_notification("LH:x", "new", "kakao")
        store.delete("LH:x")
        assert store.has_notified("LH:x", "new") is False
    finally:
        store.close()
