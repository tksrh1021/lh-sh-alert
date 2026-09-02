import json

import httpx
import pytest

from src.notifier import kakao


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_send_kakao_success(monkeypatch):
    monkeypatch.setattr(kakao, "load_env", lambda: {
        "KAKAO_REST_API_KEY": "key", "KAKAO_REFRESH_TOKEN": "refresh",
    })
    monkeypatch.setattr(kakao, "save_env", lambda updates: None)

    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if url == kakao.TOKEN_URL:
            return FakeResponse({"access_token": "abc"})
        return FakeResponse({"result_code": 0})

    monkeypatch.setattr(httpx, "post", fake_post)

    kakao.send_kakao("테스트 메시지")
    assert calls == [kakao.TOKEN_URL, kakao.SEND_URL]


def test_send_kakao_without_link_still_includes_fallback_link(monkeypatch):
    """카카오 'text' 템플릿은 link가 없으면 API가 통째로 거부한다(실제로 겪은 버그).
    LH 공고는 detail_url이 항상 None이라 이 케이스가 실전에서 항상 발생함."""
    monkeypatch.setattr(kakao, "load_env", lambda: {
        "KAKAO_REST_API_KEY": "key", "KAKAO_REFRESH_TOKEN": "refresh",
    })
    monkeypatch.setattr(kakao, "save_env", lambda updates: None)

    sent_payload = {}

    def fake_post(url, **kwargs):
        if url == kakao.TOKEN_URL:
            return FakeResponse({"access_token": "abc"})
        sent_payload.update(kwargs.get("data", {}))
        return FakeResponse({"result_code": 0})

    monkeypatch.setattr(httpx, "post", fake_post)

    kakao.send_kakao("테스트 메시지", link_url=None)

    template = json.loads(sent_payload["template_object"])
    assert "link" in template
    assert template["link"]["web_url"] == kakao.FALLBACK_LINK


def test_missing_credentials_raises(monkeypatch):
    monkeypatch.setattr(kakao, "load_env", lambda: {})
    with pytest.raises(kakao.KakaoSendError):
        kakao.send_kakao("테스트")


def test_refresh_failure_raises(monkeypatch):
    monkeypatch.setattr(kakao, "load_env", lambda: {
        "KAKAO_REST_API_KEY": "key", "KAKAO_REFRESH_TOKEN": "expired",
    })
    monkeypatch.setattr(httpx, "post", lambda url, **kw: FakeResponse({"error": "invalid_grant"}))

    with pytest.raises(kakao.KakaoSendError):
        kakao.send_kakao("테스트")


def test_send_failure_raises(monkeypatch):
    monkeypatch.setattr(kakao, "load_env", lambda: {
        "KAKAO_REST_API_KEY": "key", "KAKAO_REFRESH_TOKEN": "refresh",
    })
    monkeypatch.setattr(kakao, "save_env", lambda updates: None)

    def fake_post(url, **kwargs):
        if url == kakao.TOKEN_URL:
            return FakeResponse({"access_token": "abc"})
        return FakeResponse({"result_code": -1, "msg": "over quota"})

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(kakao.KakaoSendError):
        kakao.send_kakao("테스트")
