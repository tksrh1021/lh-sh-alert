"""LH/SH 각각의 원본 raw dict를 공통 Notice 스키마로 변환."""
import hashlib
import re
from datetime import datetime

from src.config import HOUSING_TYPE_KEYWORDS, TARGET_GROUP_KEYWORDS
from src.models import Notice

_LEADING_NEW = re.compile(r"^NEW")
_TRAILING_DAY_BADGE = re.compile(r"\d+일전$")


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
    return Notice(
        id=f"SH:{row['seq']}",
        source="SH",
        source_notice_id=row["seq"],
        title=title,
        housing_type=guess_housing_type(title),
        target_groups=guess_target_groups(title),
        regions=["서울특별시"],
        posted_at=posted_at,
        detail_url=row["detail_url"],
        raw=row,
        content_hash=_hash(title, row["posted_at"]),
    )
