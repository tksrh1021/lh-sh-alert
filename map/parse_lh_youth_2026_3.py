"""서울지역본부 26년 3차 청년 매입임대주택 예비입주자 모집공고 첨부 엑셀
(공급주택목록.xlsx)에서 주소별 단지/호실 목록을 뽑아
map/data/lh-youth-2026-3.json으로 만든다. python -m map.parse_lh_youth_2026_3

SH 행복주택과 달리 이 공고는 표가 이미 정리된 엑셀로 첨부돼 있어서
pdfplumber로 PDF 표를 뽑을 필요가 없다. 헤더는 8행짜리 병합 헤더(6~8행),
실제 데이터는 9행부터. 열 순서는 실측 확인한 고정 위치 그대로 사용.
"""
import json
import re

import openpyxl

XLSX_PATH = "research/samples/lh_2026_3_youth_seoul_housing_list.xlsx"
OUT_PATH = "map/data/lh-youth-2026-3.json"
SHEET_NAME = "청년매입임대 주택목록"
DATA_START_ROW = 9


def _gu(address):
    m = re.search(r"(\S+구)\s", address)
    return m.group(1) if m else None


def _num(v):
    return int(v) if isinstance(v, (int, float)) else None


def parse_rows(ws):
    rows = []
    for r in range(DATA_START_ROW, ws.max_row + 1):
        no = ws.cell(row=r, column=1).value
        if no is None:
            continue
        rows.append({
            "housingGroup": ws.cell(row=r, column=8).value,
            "address": ws.cell(row=r, column=5).value.strip(),
            "dong": (ws.cell(row=r, column=6).value or "").strip() or None,
            "ho": str(ws.cell(row=r, column=7).value or "").strip() or None,
            "housingType": ws.cell(row=r, column=18).value,
            "genderUse": ws.cell(row=r, column=11).value,
            "rooms": str(ws.cell(row=r, column=15).value or "").strip() or None,
            "floor": ws.cell(row=r, column=16).value,
            "elevator": ws.cell(row=r, column=17).value,
            "area": {
                "private": ws.cell(row=r, column=12).value,
                "sharedRes": ws.cell(row=r, column=13).value,
                "total": ws.cell(row=r, column=14).value,
            },
            "variants": [
                {
                    "rank": "청년1순위",
                    "base": {"deposit": _num(ws.cell(row=r, column=19).value), "rent": _num(ws.cell(row=r, column=20).value)},
                    "convert": {"deposit": _num(ws.cell(row=r, column=21).value), "rent": _num(ws.cell(row=r, column=22).value)},
                },
                {
                    "rank": "청년2,3순위",
                    "base": {"deposit": _num(ws.cell(row=r, column=23).value), "rent": _num(ws.cell(row=r, column=24).value)},
                    "convert": {"deposit": _num(ws.cell(row=r, column=25).value), "rent": _num(ws.cell(row=r, column=26).value)},
                },
            ],
        })
    return rows


def main():
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    rows = parse_rows(wb[SHEET_NAME])

    properties = {}
    for row in rows:
        addr = row["address"]
        prop = properties.setdefault(addr, {
            "address": addr,
            "gu": _gu(addr),
            "housingGroups": set(),
            "units": [],
        })
        prop["housingGroups"].add(row["housingGroup"])
        prop["units"].append({k: v for k, v in row.items() if k not in ("address", "housingGroup")})

    result = []
    for prop in properties.values():
        prop["housingGroups"] = sorted(prop["housingGroups"])
        result.append(prop)

    total_units = sum(len(p["units"]) for p in result)
    print(f"주소(마커) {len(result)}개, 호실(유닛) {total_units}개")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("저장:", OUT_PATH)


if __name__ == "__main__":
    main()
