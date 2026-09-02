from datetime import date

from src.jobs import enrich as enrich_job
from src.models import Notice
from src.store import Store


def make_lh_notice(**overrides) -> Notice:
    base = dict(
        id="LH:1",
        source="LH",
        source_notice_id="1",
        title="행복주택 테스트 공고",
        housing_type="행복주택",
        regions=["서울특별시"],
        apply_end=date(2099, 1, 1),
        raw={"file_ids": {"panId": "1", "uppAisTpCd": "06", "aisTpCd": "10", "ccrCnntSysDsCd": "03", "lsSst": ""}},
        content_hash="h",
    )
    base.update(overrides)
    return Notice(**base)


def make_sh_notice(**overrides) -> Notice:
    base = dict(
        id="SH:1",
        source="SH",
        source_notice_id="1",
        title="행복주택 테스트 공고",
        housing_type="행복주택",
        regions=["서울특별시"],
        apply_end=date(2099, 1, 1),
        raw={"detail_text": "만 19세 이상 만 39세 이하인 자"},
        content_hash="h",
    )
    base.update(overrides)
    return Notice(**base)


def test_enriches_sh_from_already_fetched_detail_text(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_sh_notice())
    store.close()

    monkeypatch.setattr(enrich_job, "DB_PATH", db_path)
    result = enrich_job.run()

    assert len(result["enriched"]) == 1
    notice, conditions = result["enriched"][0]
    assert conditions["age_min"] == 19
    assert conditions["age_max"] == 39


def test_enriches_lh_via_pdf_extraction(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_lh_notice())
    store.close()

    monkeypatch.setattr(enrich_job, "DB_PATH", db_path)
    monkeypatch.setattr(enrich_job, "extract_lh_pdf_text", lambda file_ids: "만 20세 이상 만 40세 이하")

    result = enrich_job.run()
    assert len(result["enriched"]) == 1
    _, conditions = result["enriched"][0]
    assert conditions["age_min"] == 20


def test_skips_already_enriched_notice(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_sh_notice())
    store.set_conditions("SH:1", {"age_min": 19, "age_max": 39, "extraction_confidence": 1.0})
    store.close()

    monkeypatch.setattr(enrich_job, "DB_PATH", db_path)
    result = enrich_job.run()
    assert result["enriched"] == []


def test_skips_no_match_notice_to_avoid_wasted_pdf_fetch(tmp_path, monkeypatch):
    db_path = tmp_path / "notices.db"
    store = Store(db_path)
    store.upsert(make_lh_notice(housing_type="영구임대", regions=["충청북도"]))  # NO_MATCH 확실
    store.close()

    monkeypatch.setattr(enrich_job, "DB_PATH", db_path)
    monkeypatch.setattr(
        enrich_job, "extract_lh_pdf_text",
        lambda file_ids: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")),
    )

    result = enrich_job.run()
    assert result["enriched"] == []
