from pathlib import Path

import pdfplumber

from src.enricher.condition_parse import parse_age_range, parse_conditions

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "lh_sample.pdf"


def _extract_fixture_text() -> str:
    with pdfplumber.open(FIXTURE_PDF) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_parse_age_range_from_sentence():
    text = "만 19세 이상 만 39세 이하인 자(출생일 1986.08.31. ~ 2007.08.30.)"
    assert parse_age_range(text) == (19, 39)


def test_parse_age_range_missing_returns_none_none():
    assert parse_age_range("나이 조건 없음") == (None, None)


def test_parse_conditions_on_real_lh_pdf():
    text = _extract_fixture_text()
    result = parse_conditions(text, "pdf")

    assert result["age_min"] == 19
    assert result["age_max"] == 39
    assert result["total_asset_limit_krw"] == 345_000_000
    assert result["car_value_limit_krw"] == 45_420_000
    assert result["extraction_confidence"] == 1.0
    assert result["extraction_source"] == "pdf"


def test_parse_conditions_returns_none_fields_when_nothing_found():
    result = parse_conditions("아무 조건도 안 적혀있는 평범한 문서입니다.", "pdf")
    assert result["age_min"] is None
    assert result["total_asset_limit_krw"] is None
    assert result["car_value_limit_krw"] is None
    assert result["extraction_confidence"] == 0.0


def test_asset_anchor_does_not_pick_up_unrelated_car_amount():
    # "총자산" 근처라도 실제로는 자동차가액 문장이면 총자산 값으로 오인하면 안 됨
    text = "해당 세대가 보유하고 있는 총 자산 중 자동차가액이 4,542만원 이하"
    result = parse_conditions(text, "pdf")
    assert result["total_asset_limit_krw"] is None
    assert result["car_value_limit_krw"] == 45_420_000
