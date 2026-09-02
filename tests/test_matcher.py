from datetime import date

from src.matcher import match
from src.models import Notice
from src.profile import load_profile

PROFILE = load_profile("profile.example.yaml")  # 관심유형: 행복주택 등, 거주/근무: 서울특별시


def make_notice(**overrides) -> Notice:
    base = dict(
        id="LH:1",
        source="LH",
        source_notice_id="1",
        title="테스트 공고",
        housing_type="행복주택",
        regions=["서울특별시"],
        apply_end=date(2099, 1, 1),
        content_hash="h",
    )
    base.update(overrides)
    return Notice(**base)


def test_wrong_housing_type_is_no_match():
    notice = make_notice(housing_type="상가")
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "유형" in result.reasons[0]


def test_wrong_region_is_no_match():
    notice = make_notice(regions=["충청북도"])
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "지역" in result.reasons[0]


def test_deadline_passed_is_no_match():
    notice = make_notice(apply_end=date(2020, 1, 1))
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "마감" in result.reasons[0]


def test_missing_fields_fall_back_to_needs_review_not_no_match():
    notice = make_notice(housing_type=None, regions=[], apply_end=None)
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NEEDS_REVIEW"
    assert any("유형" in r for r in result.reasons)
    assert any("지역" in r for r in result.reasons)
    assert any("마감일" in r for r in result.reasons)


def test_valid_candidate_is_needs_review_until_conditions_exist():
    notice = make_notice()
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NEEDS_REVIEW"
    assert any("세부 자격조건" in r for r in result.reasons)
