"""설계서 6장 매칭 엔진.

Phase 4(조건 자동 추출)가 아직 없어서 notice.conditions는 항상 비어 있다.
그래서 지금 걸러낼 수 있는 건 유형·지역·마감일뿐이고, 나이·소득·자산처럼
공고문을 읽어야 아는 조건은 전부 NEEDS_REVIEW로 넘긴다. "확실한 것만 걸러내고
나머지는 사람이 본다"는 설계서 6.1 원칙 그대로.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from src.models import Notice
from src.profile import Profile

Verdict = Literal["MATCH", "NEEDS_REVIEW", "NO_MATCH"]


class MatchResult(BaseModel):
    notice_id: str
    verdict: Verdict
    reasons: list[str]


def _allowed_regions(profile: Profile) -> set[str]:
    return {profile.location.residence, profile.location.workplace}


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

    allowed = _allowed_regions(profile)
    if notice.regions and not (set(notice.regions) & allowed):
        return MatchResult(
            notice_id=notice.id,
            verdict="NO_MATCH",
            reasons=[f"지역 불일치: {notice.regions}는 거주/근무지({sorted(allowed)})와 무관"],
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

    # ponytail: 나이/소득/자산 조건은 notice.conditions가 채워지는 Phase 4부터 검사한다.
    # 그때까진 이 필터를 통과해도 MATCH가 아니라 NEEDS_REVIEW까지만 올라간다.
    reasons.append("나이·소득·자산 등 세부 자격조건은 아직 자동 추출 전 — 공고문 원문에서 직접 확인 필요")

    return MatchResult(notice_id=notice.id, verdict="NEEDS_REVIEW", reasons=reasons)
