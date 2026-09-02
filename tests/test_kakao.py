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
