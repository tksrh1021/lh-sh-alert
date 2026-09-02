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


# PROFILE: birth_date 1995-01-01 -> 2026-01-01 기준 만 31세, 자산/차량 0원


def test_conditions_age_out_of_range_is_no_match():
    notice = make_notice(conditions={"age_min": 19, "age_max": 29, "extraction_confidence": 1.0})
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "나이" in result.reasons[0]


def test_conditions_asset_over_limit_is_no_match():
    notice = make_notice(conditions={"total_asset_limit_krw": 100_000_000, "extraction_confidence": 0.5})
    profile = PROFILE.model_copy(deep=True)
    profile.assets.total_asset_krw = 200_000_000  # 기준 초과
    result = match(notice, profile, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "총자산" in result.reasons[0]


def test_conditions_car_value_over_limit_is_no_match():
    notice = make_notice(conditions={"car_value_limit_krw": 10_000_000, "extraction_confidence": 0.5})
    profile = PROFILE.model_copy(deep=True)
    profile.assets.car_value_krw = 20_000_000  # 기준 초과
    result = match(notice, profile, today=date(2026, 1, 1))
    assert result.verdict == "NO_MATCH"
    assert "차량가액" in result.reasons[0]


def test_conditions_all_satisfied_promotes_to_match():
    notice = make_notice(conditions={
        "age_min": 19, "age_max": 39,
        "total_asset_limit_krw": 345_000_000,
        "car_value_limit_krw": 45_420_000,
        "extraction_confidence": 1.0,
    })
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "MATCH"


def test_conditions_with_zero_confidence_is_treated_as_no_conditions():
    notice = make_notice(conditions={"age_min": None, "age_max": None, "extraction_confidence": 0.0})
    result = match(notice, PROFILE, today=date(2026, 1, 1))
    assert result.verdict == "NEEDS_REVIEW"
