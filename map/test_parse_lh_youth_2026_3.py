import openpyxl

from map.parse_lh_youth_2026_3 import SHEET_NAME, XLSX_PATH, _gu, parse_rows


def test_parses_known_values_and_groups_by_address():
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    rows = parse_rows(wb[SHEET_NAME])

    assert len(rows) == 420  # 공고문 PDF의 "(모집호수) 총 420호"와 일치해야 함

    addresses = {r["address"] for r in rows}
    assert len(addresses) == 119

    # 같은 주소에 여러 호실이 있는 대표 사례(도시형생활주택 2개 호실)
    same_addr = [r for r in rows if r["address"] == "서울특별시 강동구 천호대로177길 39(길동) 거산 유팰리스 2차"]
    assert len(same_addr) == 2
    assert {r["ho"] for r in same_addr} == {"405", "1207"}

    # 순위별 임대조건(청년1순위/청년2,3순위)이 둘 다 채워져 있어야 함
    for r in rows:
        ranks = {v["rank"] for v in r["variants"]}
        assert ranks == {"청년1순위", "청년2,3순위"}
        for v in r["variants"]:
            assert v["base"]["deposit"] is not None
            assert v["convert"]["deposit"] is not None


def test_gu_extracted_from_address():
    assert _gu("서울특별시 강남구 논현로12길 23-5(개포동,T&K개포) T&K개포") == "강남구"
    assert _gu("서울특별시 강동구 고덕로83길 158-7(고덕동) ") == "강동구"
