"""설계서 5.3절 profile.yaml 로더. pydantic으로 필수 필드/타입을 강제한다."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel


class Personal(BaseModel):
    birth_date: date
    marital_status: str
    household_size: int
    is_homeowner: bool


class Income(BaseModel):
    monthly_gross_krw: int
    basis: str
    employment_status: str
    work_start_date: date


class Assets(BaseModel):
    total_asset_krw: int
    car_value_krw: int


class Location(BaseModel):
    residence: str
    residence_since: date
    workplace: str
    preferred_districts: list[str] = []


class Subscription(BaseModel):
    has_housing_account: bool
    opened_at: date
    deposit_count: int


class Interests(BaseModel):
    housing_types: list[str] = []
    target_groups: list[str] = []
    max_deposit_krw: int | None = None
    max_monthly_rent_krw: int | None = None


class Notify(BaseModel):
    channels: list[str] = []
    quiet_hours: str | None = None


class Profile(BaseModel):
    personal: Personal
    income: Income
    assets: Assets
    location: Location
    subscription: Subscription
    interests: Interests
    notify: Notify


def load_profile(path: str | Path) -> Profile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Profile(**data)
