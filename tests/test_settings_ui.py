import http.server
import threading
from datetime import date

import httpx
import pytest
import yaml

from src.jobs import settings_ui
from src.models import Notice
from src.store import Store


def test_chips_marks_selected_options_as_checked():
    html = settings_ui._chips("regions", ["서울특별시", "경기도"], ["서울특별시"])
    assert 'value="서울특별시" checked' in html
    assert "경기도" in html
    assert 'value="경기도" checked' not in html  # 선택 안 된 건 checked 없이


def test_render_form_includes_current_values():
    html = settings_ui._render_form({
        "personal": {"birth_date": "1995-01-01"},
        "interests": {"housing_types": ["행복주택"], "regions": ["서울특별시"], "target_groups": []},
        "notify": {"quiet_hours": "23:00-08:00"},
    })
    assert "1995-01-01" in html
    assert "행복주택" in html
    assert "서울특별시" in html
    assert 'name="quiet_start" value="23:00"' in html
    assert 'name="quiet_end" value="08:00"' in html
    assert "총자산" not in html  # 자산/차량가액 필드는 뺌


@pytest.fixture()
def running_server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.example.yaml").write_text(
        yaml.safe_dump({
            "personal": {"birth_date": "1995-01-01"},
            "interests": {"housing_types": ["행복주택"], "target_groups": [], "regions": ["서울특별시"]},
            "notify": {"quiet_hours": None},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_ui, "PROFILE_PATH", tmp_path / "profile.yaml")
    monkeypatch.setattr(settings_ui, "EXAMPLE_PATH", tmp_path / "profile.example.yaml")
    monkeypatch.setattr(settings_ui, "DB_PATH", tmp_path / "notices.db")

    saved_secrets = []
    monkeypatch.setattr(settings_ui, "set_secret", lambda name, value: saved_secrets.append((name, value)))

    server = http.server.HTTPServer(("127.0.0.1", 0), settings_ui.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port, tmp_path, saved_secrets
    server.shutdown()


def test_get_serves_form(running_server):
    port, _, _ = running_server
    resp = httpx.get(f"http://127.0.0.1:{port}/")
    assert resp.status_code == 200
    assert "생년월일" in resp.text


def test_post_saves_profile_and_pushes_secret(running_server):
    port, tmp_path, saved_secrets = running_server
    resp = httpx.post(
        f"http://127.0.0.1:{port}/save",
        data={
            "birth_date": "1998-05-20",
            "housing_types": ["행복주택", "청년안심주택"],
            "target_groups": ["청년"],
            "regions": ["서울특별시", "경기도"],
            "quiet_start": "22:00",
            "quiet_end": "07:00",
        },
    )
    assert resp.status_code == 200
    assert "저장 완료" in resp.text

    saved = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))
    assert saved["personal"]["birth_date"] == "1998-05-20"
    assert saved["interests"]["regions"] == ["서울특별시", "경기도"]
    assert saved["notify"]["quiet_hours"] == "22:00-07:00"
    assert "assets" not in saved

    assert len(saved_secrets) == 1
    assert saved_secrets[0][0] == "PROFILE_YAML"


def test_post_no_regions_checked_means_all_regions(running_server):
    port, tmp_path, _ = running_server
    httpx.post(
        f"http://127.0.0.1:{port}/save",
        data={"birth_date": "1998-05-20", "quiet_start": "22:00", "quiet_end": "07:00"},
    )
    saved = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))
    assert saved["interests"]["regions"] == []


def test_post_invalid_birth_date_shows_error(running_server):
    port, tmp_path, saved_secrets = running_server
    resp = httpx.post(
        f"http://127.0.0.1:{port}/save",
        data={"birth_date": "이건 날짜가 아님", "regions": ["서울특별시"]},
    )
    assert "저장 실패" in resp.text
    assert not (tmp_path / "profile.yaml").exists()
    assert saved_secrets == []


def _make_notice(id_, apply_start=None, apply_end=None, housing_type="행복주택", regions=None) -> Notice:
    return Notice(
        id=id_, source="LH", source_notice_id=id_, title=f"테스트 공고 {id_}",
        housing_type=housing_type, regions=regions or ["서울특별시"],
        apply_start=apply_start, apply_end=apply_end, content_hash=id_,
    )


def test_calendar_page_renders_current_month(running_server):
    port, _, _ = running_server
    resp = httpx.get(f"http://127.0.0.1:{port}/calendar")
    assert resp.status_code == 200
    assert "공고 캘린더" in resp.text


def test_calendar_day_shows_matched_notice_on_its_date(running_server):
    port, tmp_path, _ = running_server
    store = Store(tmp_path / "notices.db")
    store.upsert(_make_notice("LH:1", apply_start=date(2026, 9, 14)))
    store.close()

    resp = httpx.get(f"http://127.0.0.1:{port}/calendar/day?date=2026-09-14")
    assert "테스트 공고 LH:1" in resp.text
    assert "접수시작" in resp.text


def test_calendar_day_excludes_no_match_notice(running_server):
    port, tmp_path, _ = running_server
    store = Store(tmp_path / "notices.db")
    # 관심 유형(행복주택 등)이 아니라 확실히 NO_MATCH
    store.upsert(_make_notice("LH:2", apply_start=date(2026, 9, 14), housing_type="상가"))
    store.close()

    resp = httpx.get(f"http://127.0.0.1:{port}/calendar/day?date=2026-09-14")
    assert "테스트 공고 LH:2" not in resp.text
    assert "해당하는 공고가 없습니다" in resp.text
