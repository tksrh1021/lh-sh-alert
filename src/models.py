"""설계서 5.1절 Notice 스키마.

Phase 1에서는 목록 페이지에서 바로 얻을 수 있는 정보까지만 채운다.
접수 시각(시:분)까지 정확히 뽑는 건 Phase 4(조건 자동 추출)의 몫이라
posted_at/apply_start/apply_end는 date까지만 다룬다.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class Notice(BaseModel):
    id: str  # f"{source}:{source_notice_id}"
    source: Literal["LH", "SH"]
    source_notice_id: str
    title: str
    housing_type: str | None = None
    target_groups: list[str] = []
    regions: list[str] = []
    posted_at: date | None = None
    apply_start: date | None = None
    apply_end: date | None = None
    detail_url: str | None = None
    pdf_urls: list[str] = []
    raw: dict = {}
    conditions: dict | None = None  # Phase 4에서 채움
    first_seen_at: datetime | None = None
    updated_at: datetime | None = None
    content_hash: str
