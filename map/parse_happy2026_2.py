"""2026년 2차 행복주택 공고문 PDF에서 단지 주소/공급현황/임대금액 표를 뽑아
map/data/happy2026-2.json으로 합친다. python -m map.parse_happy2026_2

표마다 병합된 셀(단지명, 공급유형 등)이 위 행 값을 그대로 이어받는 형태라
직전 값으로 forward-fill 하는 게 핵심. 헤더 반복 행은 텍스트로 식별해서 건너뜀.
"""
import json
import re

import pdfplumber

PDF_PATH = "research/samples/sh_happy_2026_2.pdf"
OUT_PATH = "map/data/happy2026-2.json"


def _num(s):
    if not s:
        return None
    cleaned = re.sub(r"[^\d-]", "", s)
    return int(cleaned) if cleaned and cleaned != "-" else None


def _flat(s):
    return s.replace("\n", "") if s else s


def _norm(s):
    """줄바꿈 위치가 표마다 달라 원래 있던 공백이 지워지거나 살아남는 게
    다르고, 전각/반각 괄호가 표마다 섞여 있어서 매칭용 키에서는 둘 다 없앤다."""
    if not s:
        return s
    return re.sub(r"\s+", "", s).replace("（", "(").replace("）", ")")


def parse_address_table(pdf):
    rows = []
    for page in pdf.pages[50:52]:  # 문서 51~52쪽
        for t in page.extract_tables():
            rows.extend(t)
    out = {}
    kind = None
    for r in rows:
        if r[1] == "공급단지":
            continue
        if r[0]:
            kind = r[0]
        name = _flat(r[1])
        out[_norm(name)] = {
            "name": name,
            "kind": kind,
            "owner": r[2],
            "address": r[3],
            "heating": r[4],
        }
    return out


def parse_supply_table(pdf):
    """공급현황(11~15쪽): 신규(11쪽, households=계/우선/일반)와
    재공급(12~15쪽, households=합계/우선(A)/일반(A)/예비(B))은 컬럼 뜻이 다르다."""
    units = []
    gu = complex_name = type_m2 = group = None
    area_cache = {}  # (단지,면적유형)별 마지막 계약면적 — 그룹이 바뀌어도 같은 면적유형이면 공유되는 셀이 있어서 그룹과 별개로 캐시해야 함

    def add_row(kind, r):
        nonlocal gu, complex_name, type_m2, group
        if r[0]:
            gu = _flat(r[0])
        if r[1]:
            complex_name = _flat(r[1])
        if r[2]:
            type_m2 = r[2]
        if r[3]:
            group = _flat(r[3])
        income = r[4]
        if kind == "신규":
            total, priority, general, waitlist = _num(r[5]), _num(r[6]), _num(r[7]), None
            deposit, dp, balance, rent = _num(r[8]), _num(r[9]), _num(r[10]), _num(r[11])
            area = [r[12], r[13], r[14], r[15]]
        else:
            total, vac_priority, vac_general, waitlist = _num(r[5]), _num(r[6]), _num(r[7]), _num(r[8])
            priority, general = vac_priority, vac_general
            deposit, dp, balance, rent = _num(r[9]), _num(r[10]), _num(r[11]), _num(r[12])
            area = [r[13], r[14], r[15], r[16]]
        if not group or deposit is None:
            return

        area_key = (complex_name, type_m2)
        if any(area):
            area_cache[area_key] = area
        else:
            area = area_cache.get(area_key, area)

        units.append({
            "gu": gu, "complex": _norm(complex_name), "type": type_m2, "group": group, "income": income,
            "total": total, "priority": priority, "general": general, "waitlist": waitlist,
            "deposit": deposit, "dp": dp, "balance": balance, "rent": rent,
            "area": {"private": area[0], "sharedRes": area[1], "sharedOther": area[2], "total": area[3]},
        })

    page11_rows = pdf.pages[10].extract_tables()[0]
    for r in page11_rows:
        if r[1] == "단지명" or r[5] == "계":
            continue
        add_row("신규", r)

    for page in pdf.pages[11:15]:  # 12~15쪽
        for t in page.extract_tables():
            for r in t:
                if r[1] == "단지명":
                    continue
                add_row("재공급", r)
    return units


def parse_convert_table(pdf):
    """임대금액 상세 안내(별표1, 53~56쪽): 단지명/공급유형/공급구분 forward-fill."""
    rows = []
    for page in pdf.pages[52:56]:  # 문서 53~56쪽
        for t in page.extract_tables():
            rows.extend(t)
    out = {}
    complex_name = type_m2 = group = None
    for r in rows:
        if r[0] == "단지명" or r[4] in (None, "기준 임대 조건") or r[4] == "임대보증금(천원)":
            continue
        if r[0]:
            complex_name = _flat(r[0])
        if r[1]:
            type_m2 = r[1]
        if r[2]:
            group = _flat(r[2])
        income = r[3]
        if not r[4] or not re.search(r"\d", r[4]):
            continue
        deposit, rent = _num(r[4]), _num(r[7])
        key = (_norm(complex_name), type_m2, group, income)
        out[key] = {
            "base": {"deposit": deposit, "rent": rent},
            "convertUp": {"deposit": _num(r[8]), "rent": _num(r[9])},
            "convertDown": {"deposit": _num(r[10]), "rent": _num(r[11])},
        }
    return out


def main():
    with pdfplumber.open(PDF_PATH) as pdf:
        addresses = parse_address_table(pdf)
        units = parse_supply_table(pdf)
        conversions = parse_convert_table(pdf)

    complexes = {}
    missing_convert = []
    # 소득있음/없음처럼 같은 (단지,면적,계층) 안에서 갈리는 행은 세대수·면적을
    # 공유하고 임대조건만 다르다 — PDF에서 이어지는 행이 세대수 칸을 비워두는
    # 이유. unit 하나에 income별 variants로 모아야 "-세대"처럼 깨져 보이지 않는다.
    unit_groups = {}
    for u in units:
        unit_key = (u["complex"], u["type"], u["group"])
        group = unit_groups.setdefault(unit_key, {"total": None, "priority": None, "general": None, "waitlist": None, "area": None, "variants": []})
        if u["total"] is not None:
            group["total"], group["priority"], group["general"], group["waitlist"] = u["total"], u["priority"], u["general"], u["waitlist"]
        if any(v for v in u["area"].values()):
            group["area"] = u["area"]

        conv_key = (u["complex"], u["type"], u["group"], u["income"])
        conv = conversions.get(conv_key)
        if conv is None:
            missing_convert.append(conv_key)
        group["variants"].append({"income": u["income"], **(conv or {})})

    for (complex_name, type_m2, group_name), g in unit_groups.items():
        c = complexes.setdefault(
            complex_name, {**addresses.get(complex_name, {"name": complex_name}), "gu": None, "units": []}
        )
        c["gu"] = c["gu"] or next(u["gu"] for u in units if u["complex"] == complex_name)
        c["units"].append({
            "type": type_m2, "group": group_name,
            "households": {"total": g["total"], "priority": g["priority"], "general": g["general"], "waitlist": g["waitlist"]},
            "area": g["area"],
            "variants": g["variants"],
        })

    unmatched_address = [name for name in complexes if name not in addresses]
    print(f"단지 {len(complexes)}개, 유닛 {len(units)}개, 전환정보 누락 {len(missing_convert)}건, 주소 못찾은 단지 {len(unmatched_address)}개")
    if missing_convert:
        print("전환정보 못찾은 키:", missing_convert[:10])
    if unmatched_address:
        print("주소 못찾은 단지:", unmatched_address)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(list(complexes.values()), f, ensure_ascii=False, indent=2)
    print("저장:", OUT_PATH)


if __name__ == "__main__":
    main()
