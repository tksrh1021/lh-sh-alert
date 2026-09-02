import http.server
import threading

import httpx
import pytest
import yaml

from src.jobs import settings_ui


def test_split_csv_trims_and_drops_empty():
    assert settings_ui._split_csv("행복주택, 청년매입임대 ,, 청년안심주택") == [
        "행복주택", "청년매입임대", "청년안심주택",
    ]


def test_render_form_includes_current_values():
    html = settings_ui._render_form({
        "personal": {"birth_date": "1995-01-01"},
        "assets": {"total_asset_krw": 0, "car_value_krw": 0},
        "interests": {"housing_types": ["행복주택"], "regions": ["서울특별시"], "target_groups": []},
        "notify": {"quiet_hours": "23:00-08:00"},
    })
    assert "1995-01-01" in html
    assert "행복주택" in html
    assert "서울특별시" in html


@pytest.fixture()
def running_server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.example.yaml").write_text(
        yaml.safe_dump({
            "personal": {"birth_date": "1995-01-01"},
            "assets": {"total_asset_krw": 0, "car_value_krw": 0},
            "interests": {"housing_types": [], "target_groups": [], "regions": []},
            "notify": {"quiet_hours": None},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_ui, "PROFILE_PATH", tmp_path / "profile.yaml")
    monkeypatch.setattr(settings_ui, "EXAMPLE_PATH", tmp_path / "profile.example.yaml")

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
            "total_asset_krw": "10000000",
            "car_value_krw": "0",
            "housing_types": "행복주택, 청년안심주택",
            "target_groups": "청년",
            "regions": "서울특별시, 경기도",
            "quiet_hours": "22:00-07:00",
        },
    )
    assert resp.status_code == 200
    assert "저장 완료" in resp.text

    saved = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))
    assert saved["personal"]["birth_date"] == "1998-05-20"
    assert saved["interests"]["regions"] == ["서울특별시", "경기도"]

    assert len(saved_secrets) == 1
    assert saved_secrets[0][0] == "PROFILE_YAML"
    assert "서울특별시" in saved_secrets[0][1]


def test_post_invalid_birth_date_shows_error(running_server):
    port, tmp_path, saved_secrets = running_server
    resp = httpx.post(
        f"http://127.0.0.1:{port}/save",
        data={"birth_date": "이건 날짜가 아님", "regions": "서울특별시"},
    )
    assert "저장 실패" in resp.text
    assert not (tmp_path / "profile.yaml").exists()
    assert saved_secrets == []
