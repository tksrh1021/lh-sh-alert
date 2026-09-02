from datetime import date

from src.jobs import remind as remind_job
from src.models import Notice
from src.store import Store


def make_notice(apply_end: date, housing_type: str | None = None, regions=None) -> Notice:
    return Notice(
        id="LH:1",
        source="LH",
        source_notice_id="1",
        title="장기전세 테스트 공고",
        apply_end=apply_end,
        housing_type=housing_type,
        regions=regions or [],
        content_hash="h",
    )


def test_sends_reminder_on_matching_day_only(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_end=date(2026, 1, 4)))  # D-3
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    calls = []
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    result = remind_job.run(today=today)
    assert len(result["sent"]) == 1
    assert calls[0].count("D-3") == 1 or "D-3" in calls[0]


def test_no_reminder_on_non_matching_day(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_end=date(2026, 1, 10)))  # D-9, 리마인드 대상 아님
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")))

    result = remind_job.run(today=today)
    assert result["sent"] == []


def test_same_day_offset_not_sent_twice(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_end=date(2026, 1, 1)))  # D-0
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    calls = []
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    remind_job.run(today=today)
    remind_job.run(today=today)
    assert len(calls) == 1


def test_no_match_notice_is_not_reminded(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    # 관심 유형이 아닌 공고라 NO_MATCH -> 마감이 코앞이어도 리마인드 대상 아님
    store.upsert(make_notice(apply_end=date(2026, 1, 1), housing_type="영구임대", regions=["충청북도"]))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")))

    result = remind_job.run(today=today)
    assert result["sent"] == []
