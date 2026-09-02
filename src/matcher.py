"""설계서 6장 매칭 엔진.

유형·지역·마감일은 항상 확인한다. 나이·자산·차량가액은 notice.conditions가
채워져 있을 때만(Phase 4 enrich 이후) 검사하고, 없으면 여전히 NEEDS_REVIEW로
넘긴다. 소득은 의도적으로 검사하지 않는다 — 공고마다 표현이 달라 규칙 기반으로
안전하게 뽑기 어렵다는 판단(사용자 결정).
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from src.config import SEOUL_DISTRICTS
from src.models import Notice
from src.profile import Profile

Verdict = Literal["MATCH", "NEEDS_REVIEW", "NO_MATCH"]


class MatchResult(BaseModel):
    notice_id: str
    verdict: Verdict
    reasons: list[str]


def match(notice: Notice, profile: Profile, today: date | None = None) -> MatchResult:
    today = today or date.today()
    reasons: list[str] = []

    if notice.housing_type and notice.housing_type not in profile.interests.housing_types:
        return MatchResult(
            notice_id=notice.id,
            verdict="NO_MATCH",
            reasons=[f"관심 유형 아님: '{notice.housing_type}'은(는) 관심 목록({profile.interests.housing_types})에 없음"],
        )
    if not notice.housing_type:
        reasons.append("주택 유형을 제목에서 확인 못함 — 공고문 확인 필요")

    allowed = set(profile.interests.regions)
    if allowed and notice.regions and not (set(notice.regions) & allowed):
        # 구 단위로 좁혀놨는데 공고에서 구를 못 찾은 경우(서울인 건 맞음)엔
        # "확실히 다름"이 아니라 "모름"이라서 걸러내지 않고 사람 확인으로 넘긴다.
        wants_specific_gu = any(r in SEOUL_DISTRICTS for r in allowed) and "서울특별시" not in allowed
        district_unknown = notice.regions == ["서울특별시"]
        if wants_specific_gu and district_unknown:
            wanted_gu = sorted(allowed & set(SEOUL_DISTRICTS))
            reasons.append(f"서울 공고인데 제목에서 구를 못 찾음 — 관심 구({wanted_gu})인지 직접 확인 필요")
        else:
            return MatchResult(
                notice_id=notice.id,
                verdict="NO_MATCH",
                reasons=[f"지역 불일치: {notice.regions}는 관심 지역({sorted(allowed)})과 무관"],
            )
    if not notice.regions:
        reasons.append("지역 정보 없음 — 공고문 확인 필요")

    if notice.apply_end is not None and notice.apply_end < today:
        return MatchResult(
            notice_id=notice.id,
            verdict="NO_MATCH",
            reasons=[f"접수 마감됨: {notice.apply_end.isoformat()}"],
        )
    if notice.apply_end is None:
        reasons.append("접수 마감일 미확인 — 공고문에서 직접 확인 필요")

    if notice.target_groups and not (set(notice.target_groups) & set(profile.interests.target_groups)):
        reasons.append(f"대상 계층이 관심사와 다를 수 있음: 공고 대상={notice.target_groups}")

    if not notice.conditions or not notice.conditions.get("extraction_confidence"):
        reasons.append("나이·자산 등 세부 자격조건은 아직 자동 추출 전 — 공고문 원문에서 직접 확인 필요")
        return MatchResult(notice_id=notice.id, verdict="NEEDS_REVIEW", reasons=reasons)

    age_reject = _check_age(notice.conditions, profile, today)
    if age_reject:
        return MatchResult(notice_id=notice.id, verdict="NO_MATCH", reasons=[age_reject])

    asset_reject = _check_amount_limit(
        notice.conditions.get("total_asset_limit_krw"), profile.assets.total_asset_krw, "총자산"
    )
    if asset_reject:
        return MatchResult(notice_id=notice.id, verdict="NO_MATCH", reasons=[asset_reject])

    car_reject = _check_amount_limit(
        notice.conditions.get("car_value_limit_krw"), profile.assets.car_value_krw, "차량가액"
    )
    if car_reject:
        return MatchResult(notice_id=notice.id, verdict="NO_MATCH", reasons=[car_reject])

    reasons.append(_conditions_summary(notice.conditions))
    reasons.append("소득 조건은 자동판단 대상이 아님 — 공고문에서 직접 확인 필요")
    return MatchResult(notice_id=notice.id, verdict="MATCH", reasons=reasons)


def _applicant_age(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def _check_age(conditions: dict, profile: Profile, today: date) -> str | None:
    age_min, age_max = conditions.get("age_min"), conditions.get("age_max")
    if age_min is None and age_max is None:
        return None
    age = _applicant_age(profile.personal.birth_date, today)
    if age_min is not None and age < age_min:
        return f"나이 조건 미달: 만 {age}세 (공고 기준 만 {age_min}세 이상)"
    if age_max is not None and age > age_max:
        return f"나이 조건 초과: 만 {age}세 (공고 기준 만 {age_max}세 이하)"
    return None


def _check_amount_limit(limit_krw: int | None, my_amount_krw: int, label: str) -> str | None:
    if limit_krw is None:
        return None
    if my_amount_krw > limit_krw:
        return f"{label} 기준 초과: 내 {my_amount_krw:,}원 > 기준 {limit_krw:,}원"
    return None


def _conditions_summary(conditions: dict) -> str:
    parts = []
    if conditions.get("age_min") or conditions.get("age_max"):
        parts.append(f"나이 만 {conditions.get('age_min')}~{conditions.get('age_max')}세 조건 충족")
    if conditions.get("total_asset_limit_krw"):
        parts.append(f"총자산 기준({conditions['total_asset_limit_krw']:,}원) 이내")
    if conditions.get("car_value_limit_krw"):
        parts.append(f"차량가액 기준({conditions['car_value_limit_krw']:,}원) 이내")
    return " / ".join(parts) if parts else "자동 추출된 조건 일부만 확인됨"
