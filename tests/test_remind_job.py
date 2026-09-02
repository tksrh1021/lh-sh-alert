from datetime import date

from src.jobs import remind as remind_job
from src.models import Notice
from src.store import Store


def make_notice(apply_start=None, apply_end=None, doc_review_date=None, result_date=None,
                 housing_type=None, regions=None) -> Notice:
    return Notice(
        id="LH:1",
        source="LH",
        source_notice_id="1",
        title="장기전세 테스트 공고",
        apply_start=apply_start,
        apply_end=apply_end,
        doc_review_date=doc_review_date,
        result_date=result_date,
        housing_type=housing_type,
        regions=regions or [],
        content_hash="h",
    )


def test_sends_on_apply_start_day(tmp_path, monkeypatch):
    today = date(2026, 1, 5)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_start=today, apply_end=date(2026, 1, 10)))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    calls = []
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    result = remind_job.run(today=today)
    assert len(result["sent"]) == 1
    assert result["sent"][0][1] == "start"


def test_sends_on_apply_end_day_and_not_twice(tmp_path, monkeypatch):
    today = date(2026, 1, 10)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_start=date(2026, 1, 5), apply_end=today))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    calls = []
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    result1 = remind_job.run(today=today)
    assert len(result1["sent"]) == 1
    assert result1["sent"][0][1] == "end"

    result2 = remind_job.run(today=today)
    assert result2["sent"] == []
    assert len(calls) == 1


def test_no_reminder_on_non_matching_day(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(apply_start=date(2026, 1, 5), apply_end=date(2026, 1, 10)))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")))

    result = remind_job.run(today=today)
    assert result["sent"] == []


def test_sends_on_doc_review_and_result_dates(tmp_path, monkeypatch):
    today = date(2026, 10, 23)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_notice(doc_review_date=today, result_date=date(2026, 12, 28)))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    calls = []
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    result = remind_job.run(today=today)
    assert len(result["sent"]) == 1
    assert result["sent"][0][1] == "doc_review"

    result2 = remind_job.run(today=date(2026, 12, 28))
    assert len(result2["sent"]) == 1
    assert result2["sent"][0][1] == "result"
    assert len(calls) == 2


def test_no_match_notice_is_not_reminded(tmp_path, monkeypatch):
    today = date(2026, 1, 1)
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    # 관심 유형이 아닌 공고라 NO_MATCH -> 시작일이어도 리마인드 대상 아님
    store.upsert(make_notice(apply_start=today, housing_type="영구임대", regions=["충청북도"]))
    store.close()

    monkeypatch.setattr(remind_job, "DB_PATH", db_path)
    monkeypatch.setattr(remind_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")))

    result = remind_job.run(today=today)
    assert result["sent"] == []
