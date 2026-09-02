"""설계서 5.3절 profile.yaml 로더. pydantic으로 필수 필드/타입을 강제한다.

매처가 실제로 쓰는 필드만 남겼다(나이/관심유형/관심지역/조용한시간).
소득·세대·청약통장 등은 자동판단에 안 쓰기로 했으니 여기서도 뺐다 — 안 쓰는
입력을 UI에서 받는 건 사용자에게 혼란만 준다. 자산/차량가액은 설정 UI에서는
안 받지만(사용자 요청), matcher가 여전히 검사할 수 있게 필드 자체는 남겨뒀다 —
기본값 0이라 아무도 걸러내지 않는다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel


class Personal(BaseModel):
    birth_date: date


class Assets(BaseModel):
    total_asset_krw: int = 0
    car_value_krw: int = 0


class Interests(BaseModel):
    housing_types: list[str] = []
    target_groups: list[str] = []
    regions: list[str] = []  # 보고 싶은 시/도만 적으면 그 지역 공고만 본다


class Notify(BaseModel):
    quiet_hours: str | None = None  # "23:00-08:00" 형식, 이 시간엔 발송을 다음날 아침으로 미룸


class Profile(BaseModel):
    personal: Personal
    assets: Assets = Assets()
    interests: Interests = Interests()
    notify: Notify = Notify()


def load_profile(path: str | Path) -> Profile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Profile(**data)
