from src.normalizer import clean_title, guess_housing_type, normalize_lh, normalize_sh


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
