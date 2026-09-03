import pdfplumber

from map.parse_happy2026_2 import parse_address_table, parse_convert_table, parse_supply_table

PDF_PATH = "research/samples/sh_happy_2026_2.pdf"


def test_parses_known_values_and_joins_cleanly():
    with pdfplumber.open(PDF_PATH) as pdf:
        addresses = parse_address_table(pdf)
        units = parse_supply_table(pdf)
        conversions = parse_convert_table(pdf)

    assert len(addresses) == 62
    assert len(units) == 107  # 소득있음/없음 등 income-split 행까지 전부 포함

    gangdong11 = [u for u in units if u["complex"] == "강동리엔파크11단지"]
    assert len(gangdong11) == 3  # 청년 소득있음/소득없음 + 29S 고령자, forward-fill 안 되면 유실됨
    incomes = {u["income"] for u in gangdong11}
    assert incomes == {"소득있음", "소득없음", None}

    for u in units:
        key = (u["complex"], u["type"], u["group"], u["income"])
        assert key in conversions, f"전환정보 매칭 실패: {key}"
