"""LH/SH 각각의 원본 raw dict를 공통 Notice 스키마로 변환."""
import hashlib
import re
from datetime import date, datetime

from src.config import HOUSING_TYPE_KEYWORDS, TARGET_GROUP_KEYWORDS
from src.models import Notice

_LEADING_NEW = re.compile(r"^NEW")
_TRAILING_DAY_BADGE = re.compile(r"\d+일전$")
_SCHEDULE_DATE = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.")


def clean_title(raw_title: str) -> str:
    title = _LEADING_NEW.sub("", raw_title)
    title = _TRAILING_DAY_BADGE.sub("", title)
    return title.strip()


def guess_housing_type(title: str) -> str | None:
    for keyword in HOUSING_TYPE_KEYWORDS:
        if keyword in title:
            return keyword
    return None


def guess_target_groups(title: str) -> list[str]:
    return [kw for kw in TARGET_GROUP_KEYWORDS if kw in title]


def _parse_date(text: str, fmt: str):
    text = text.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, fmt).date()
    except ValueError:
        return None


def _hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


_SCHEDULE_STOP_MARKERS = ["서류심사", "당첨자"]


def _find_schedule_block(detail_text: str) -> str | None:
    """'청약신청'은 상단 메뉴에도 반복해서 나오는 흔한 단어라, 뒤에 날짜가 바로
    따라오는 진짜 일정 문구만 고른다. 공고마다 '청약신청 일정' / '청약신청 :' 등
    표현이 달라서 고정 문자열 대신 이 방식으로 찾는다."""
    for m in re.finditer("청약신청", detail_text):
        if detail_text[m.end() : m.end() + 1] == "서":
            continue  # "청약신청서(...).pdf" 같은 첨부파일명 오탐 방지
        window = detail_text[m.start() : m.start() + 200]
        if _SCHEDULE_DATE.search(window):
            start = m.start()
            stops = [detail_text.find(marker, start + 5) for marker in _SCHEDULE_STOP_MARKERS]
            stops = [s for s in stops if s > 0]
            end = min(stops) if stops else start + 400
            return detail_text[start:end]
    return None


def parse_schedule_dates(detail_text: str | None) -> tuple[date | None, date | None]:
    """상세 페이지 전체 텍스트에서 접수 일정 구간을 찾아, 그 안의 날짜 중
    가장 이른 날=접수시작, 가장 늦은 날=접수마감으로 잡는다. 순위별 시작·종료
    시각이 전부 그 구간 안에 있어서 구간 안의 min/max가 곧 전체 접수 시작/마감이
    된다 (FINDINGS.md 실측 확인)."""
    if not detail_text:
        return None, None
    block = _find_schedule_block(detail_text)
    if not block:
        return None, None
    matches = _SCHEDULE_DATE.findall(block)
    if not matches:
        return None, None
    dates = sorted({date(int(y), int(m), int(d)) for y, m, d in matches})
    return dates[0], dates[-1]


def _first_date_after(text: str, anchor: str, window: int = 60) -> date | None:
    idx = text.find(anchor)
    if idx < 0:
        return None
    m = _SCHEDULE_DATE.search(text[idx : idx + len(anchor) + window])
    if not m:
        return None
    y, mo, d = m.groups()
    return date(int(y), int(mo), int(d))


def parse_review_dates(detail_text: str | None) -> tuple[date | None, date | None]:
    """서류심사대상자 발표일, 당첨자 발표일. 표현이 조금씩 달라 후보를 여러 개 시도한다
    (F-11: 실측에서 '발표: 2026...'처럼 콜론 앞 공백 없는 경우와 있는 경우가 둘 다 있었음
    — 콜론 자체는 매칭에 안 쓰고 앵커 뒤 구간에서 날짜만 찾아서 신경 안 써도 됨)."""
    if not detail_text:
        return None, None
    doc_review = (
        _first_date_after(detail_text, "서류심사대상자 발표")
        or _first_date_after(detail_text, "서류심사 대상자 발표")
        or _first_date_after(detail_text, "서류심사결과 발표")
    )
    result = (
        _first_date_after(detail_text, "당첨자 및 예비자 발표")
        or _first_date_after(detail_text, "당첨자발표")
        or _first_date_after(detail_text, "당첨자 발표")
    )
    return doc_review, result


def normalize_lh(row: dict) -> Notice:
    title = clean_title(row["title"])
    posted_at = _parse_date(row["posted_at"], "%Y.%m.%d")
    apply_end = _parse_date(row["deadline"], "%Y.%m.%d")
    return Notice(
        id=f"LH:{row['pan_id']}",
        source="LH",
        source_notice_id=row["pan_id"],
        title=title,
        housing_type=row["housing_type"] or None,
        target_groups=guess_target_groups(title),
        regions=[row["region"]] if row.get("region") else [],
        posted_at=posted_at,
        apply_end=apply_end,
        detail_url=None,  # 상세보기는 NetFunnel 게이트라 링크 제공 안 함
        raw=row,
        content_hash=_hash(title, row["posted_at"], row["deadline"], row["status"]),
    )


def normalize_sh(row: dict) -> Notice:
    title = clean_title(row["title"])
    posted_at = _parse_date(row["posted_at"], "%Y-%m-%d")
    detail_text = row.get("detail_text")
    apply_start, apply_end = parse_schedule_dates(detail_text)
    doc_review_date, result_date = parse_review_dates(detail_text)
    return Notice(
        id=f"SH:{row['seq']}",
        source="SH",
        source_notice_id=row["seq"],
        title=title,
        housing_type=guess_housing_type(title),
        target_groups=guess_target_groups(title),
        regions=["서울특별시"],
        posted_at=posted_at,
        apply_start=apply_start,
        apply_end=apply_end,
        doc_review_date=doc_review_date,
        result_date=result_date,
        detail_url=row["detail_url"],
        raw=row,
        content_hash=_hash(
            title, row["posted_at"], str(apply_start), str(apply_end),
            str(doc_review_date), str(result_date),
        ),
    )
