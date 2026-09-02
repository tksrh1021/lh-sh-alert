from src.models import Notice
from src.store import Store


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
