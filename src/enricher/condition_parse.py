"""공고문 텍스트에서 나이·자산·차량가액 조건만 규칙 기반으로 뽑는다.

소득은 일부러 뺐다: 가구원수 x 대상계층 x 순위로 쪼개진 퍼센트표라 공고마다
표현이 다르고, 숫자가 밀집돼 있어 잘못 짚으면(=엉뚱한 숫자를 소득기준으로
오인) 오탈락으로 직결된다. 나이/자산/차량가액은 "만 OO세 이상 OO세 이하",
"총자산가액 합산기준 OOO만원" 처럼 문장이 비교적 고정돼 있어 규칙 기반으로도
안전하게 뽑을 수 있는 것만 골랐다.

값을 못 찾으면 절대 추측하지 않고 None으로 둔다 — 매칭 엔진이 None은
'모름'으로 취급해 NEEDS_REVIEW로 넘긴다.
"""
import re

_AGE_RANGE = re.compile(r"만\s*(\d{1,3})\s*세\s*이상\s*만?\s*(\d{1,3})\s*세\s*이하")

# ponytail: 순위별로 기준액이 다를 때(완화 조건 등) 가장 관대한 값을 쓴다.
# 더 엄격한 순위를 놓치는 것보다, 신청 자체가 가능한 걸 놓치는 게 더 나쁘다.
_ASSET_ANCHORS = ["총자산가액 합산기준", "총 자산가액 합산기준", "총자산 합산기준", "총 자산 합산기준"]
_CAR_ANCHORS = ["자동차가액이", "자동차가액은", "차량가액이", "차량가액은"]


def _extract_krw(text: str) -> int | None:
    m = re.search(r"(\d+)\s*억\s*([\d,]+)?\s*만?\s*원", text)
    if m:
        eok = int(m.group(1))
        man = int(m.group(2).replace(",", "")) if m.group(2) else 0
        return eok * 100_000_000 + man * 10_000
    m = re.search(r"([\d,]+)\s*만원", text)
    if m:
        return int(m.group(1).replace(",", "")) * 10_000
    m = re.search(r"([\d,]{4,})\s*원", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _max_amount_near_anchors(text: str, anchors: list[str], window: int = 40) -> int | None:
    amounts = []
    for anchor in anchors:
        for m in re.finditer(re.escape(anchor), text):
            amount = _extract_krw(text[m.end() : m.end() + window])
            if amount:
                amounts.append(amount)
    return max(amounts) if amounts else None


def parse_age_range(text: str) -> tuple[int | None, int | None]:
    m = _AGE_RANGE.search(text)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def parse_conditions(text: str, source: str) -> dict:
    age_min, age_max = parse_age_range(text)
    asset_limit = _max_amount_near_anchors(text, _ASSET_ANCHORS)
    car_limit = _max_amount_near_anchors(text, _CAR_ANCHORS)

    found = sum(v is not None for v in (age_min, asset_limit, car_limit))
    return {
        "age_min": age_min,
        "age_max": age_max,
        "total_asset_limit_krw": asset_limit,
        "car_value_limit_krw": car_limit,
        "extraction_confidence": round(found / 3, 2),
        "extraction_source": source,
    }
