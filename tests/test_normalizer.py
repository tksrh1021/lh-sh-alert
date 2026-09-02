from datetime import date

from src.normalizer import clean_title, guess_housing_type, normalize_lh, normalize_sh, parse_schedule_dates


def test_clean_title_strips_new_prefix_and_day_badge():
    assert clean_title("NEW[정정공고]행복주택 모집1일전") == "[정정공고]행복주택 모집"
    assert clean_title("그냥 제목") == "그냥 제목"


def test_guess_housing_type_finds_keyword():
    assert guess_housing_type("2026년 행복주택 입주자 모집") == "행복주택"
    assert guess_housing_type("아무 관련 없는 제목") is None


def test_normalize_lh_builds_expected_id_and_hash():
    row = {
        "pan_id": "2015122300020676",
        "title": "NEW진천성석 행복주택 모집1일전",
        "housing_type": "행복주택",
        "region": "충청북도",
        "posted_at": "2026.09.02",
        "deadline": "2026.09.09",
        "status": "공고중",
    }
    notice = normalize_lh(row)
    assert notice.id == "LH:2015122300020676"
    assert notice.source == "LH"
    assert notice.posted_at.isoformat() == "2026-09-02"
    assert notice.apply_end.isoformat() == "2026-09-09"
    assert notice.regions == ["충청북도"]
    assert notice.title == "진천성석 행복주택 모집"


def test_normalize_sh_infers_housing_type_from_title():
    row = {
        "seq": "309467",
        "title": "제51차 장기전세주택 입주자 모집공고",
        "posted_at": "2026-09-02",
        "detail_url": "https://www.i-sh.co.kr/app/.../view.do?seq=309467&multi_itm_seq=2",
    }
    notice = normalize_sh(row)
    assert notice.id == "SH:309467"
    assert notice.housing_type == "장기전세"
    assert notice.regions == ["서울특별시"]


def test_parse_schedule_dates_takes_min_and_max():
    text = "청약신청 일정\n[1순위] 2026. 9. 14.(월) ~ 2026. 9. 15.(화)\n[3·4순위] 2026. 9. 17.(목)"
    start, end = parse_schedule_dates(text)
    assert start == date(2026, 9, 14)
    assert end == date(2026, 9, 17)


def test_parse_schedule_dates_handles_missing_text():
    assert parse_schedule_dates(None) == (None, None)
    assert parse_schedule_dates("관련 날짜 없음") == (None, None)


def test_parse_schedule_dates_ignores_menu_mentions_without_dates():
    # 상단 메뉴에 '청약신청'만 반복되고 날짜가 안 붙어있으면 진짜 일정으로 오인하면 안 됨
    text = "청약신청 청약신청 청약신청\n" * 3 + "본문...\n청약신청 :\n2026. 9. 28.(월) ~ 2026. 9. 30.(수)\n서류심사대상자 발표 : 2026. 10. 23.(금)"
    start, end = parse_schedule_dates(text)
    assert start == date(2026, 9, 28)
    assert end == date(2026, 9, 30)  # 서류심사 발표일(10.23)은 포함되면 안 됨


def test_normalize_sh_fills_apply_dates_from_detail_text():
    row = {
        "seq": "309467",
        "title": "제51차 장기전세주택 입주자 모집공고",
        "posted_at": "2026-09-02",
        "detail_url": "https://www.i-sh.co.kr/app/.../view.do?seq=309467&multi_itm_seq=2",
        "detail_text": "청약신청 일정\n[1순위] 2026. 9. 14.(월) ~ [3·4순위] 2026. 9. 17.(목)",
    }
    notice = normalize_sh(row)
    assert notice.apply_start == date(2026, 9, 14)
    assert notice.apply_end == date(2026, 9, 17)


def test_parse_schedule_dates_from_real_fixture_heading_style():
    from pathlib import Path

    from bs4 import BeautifulSoup

    html = (Path(__file__).parent / "fixtures" / "sh_detail_schedule_style.html").read_text(encoding="utf-8")
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    start, end = parse_schedule_dates(text)
    assert start == date(2026, 9, 14)
    assert end == date(2026, 9, 17)


def test_parse_schedule_dates_from_real_fixture_supply_schedule_style():
    from pathlib import Path

    from bs4 import BeautifulSoup

    html = (Path(__file__).parent / "fixtures" / "sh_detail_supply_schedule_style.html").read_text(encoding="utf-8")
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    start, end = parse_schedule_dates(text)
    assert start == date(2026, 9, 28)
    assert end == date(2026, 9, 30)


def test_same_input_produces_same_hash_different_input_differs():
    row = {
        "pan_id": "1",
        "title": "제목",
        "housing_type": "행복주택",
        "region": "서울",
        "posted_at": "2026.01.01",
        "deadline": "2026.01.10",
        "status": "공고중",
    }
    notice_a = normalize_lh(row)
    notice_b = normalize_lh({**row, "status": "정정공고중"})
    assert notice_a.content_hash != notice_b.content_hash
