from datetime import date

from src.jobs import notify as notify_job
from src.models import Notice
from src.store import Store


def make_notice(i: int) -> Notice:
    return Notice(
        id=f"LH:{i}",
        source="LH",
        source_notice_id=str(i),
        title=f"행복주택 테스트 공고 {i}",
        housing_type="행복주택",
        regions=["서울특별시"],
        apply_end=date(2099, 1, 1),
        content_hash=f"hash{i}",
    )


def setup_store(tmp_path, count=1):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    for i in range(count):
        store.upsert(make_notice(i))
    store.close()
    return db_path


def test_sends_once_then_skips_on_rerun(tmp_path, monkeypatch):
    db_path = setup_store(tmp_path, count=1)
    monkeypatch.setattr(notify_job, "DB_PATH", db_path)
    monkeypatch.setattr(notify_job, "is_quiet_now", lambda quiet_hours: False)

    sent_texts = []
    monkeypatch.setattr(notify_job, "notify", lambda text, link=None: sent_texts.append(text) or "kakao")

    result1 = notify_job.run()
    assert len(result1["sent"]) == 1
    assert len(sent_texts) == 1

    result2 = notify_job.run()
    assert len(result2["sent"]) == 0
    assert len(result2["skipped_already"]) == 1
    assert len(sent_texts) == 1  # 두 번째 실행에선 추가 발송 없음


def test_quiet_hours_skips_sending(tmp_path, monkeypatch):
    db_path = setup_store(tmp_path, count=1)
    monkeypatch.setattr(notify_job, "DB_PATH", db_path)
    monkeypatch.setattr(notify_job, "is_quiet_now", lambda quiet_hours: True)
    monkeypatch.setattr(notify_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("조용한 시간엔 호출되면 안 됨")))

    result = notify_job.run()
    assert result["sent"] == []
    assert len(result["skipped_quiet"]) == 1


def test_over_daily_cap_sends_one_summary(tmp_path, monkeypatch):
    db_path = setup_store(tmp_path, count=notify_job.DAILY_CAP + 1)
    monkeypatch.setattr(notify_job, "DB_PATH", db_path)
    monkeypatch.setattr(notify_job, "is_quiet_now", lambda quiet_hours: False)

    calls = []
    monkeypatch.setattr(notify_job, "notify", lambda text, link=None: calls.append(text) or "kakao")

    result = notify_job.run()
    assert len(calls) == 1  # 요약 메시지 1건만
    assert len(result["sent"]) == notify_job.DAILY_CAP + 1  # 전부 발송 처리(중복 방지용)
