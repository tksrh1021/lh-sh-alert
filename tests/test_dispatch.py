import pytest

from src.notifier import dispatch
from src.notifier.backup import BackupSendError
from src.notifier.kakao import KakaoSendError


def test_notify_uses_kakao_when_it_works(monkeypatch):
    monkeypatch.setattr(dispatch, "send_kakao", lambda text, link=None: None)
    monkeypatch.setattr(dispatch, "send_discord", lambda text: (_ for _ in ()).throw(AssertionError("안 불려야 함")))

    assert dispatch.notify("hello") == "kakao"


def test_notify_falls_back_to_discord_when_kakao_fails(monkeypatch):
    monkeypatch.setattr(dispatch, "send_kakao", lambda text, link=None: (_ for _ in ()).throw(KakaoSendError("token expired")))
    monkeypatch.setattr(dispatch, "send_discord", lambda text: None)

    assert dispatch.notify("hello") == "discord"


def test_notify_raises_when_both_fail(monkeypatch):
    monkeypatch.setattr(dispatch, "send_kakao", lambda text, link=None: (_ for _ in ()).throw(KakaoSendError("token expired")))
    monkeypatch.setattr(dispatch, "send_discord", lambda text: (_ for _ in ()).throw(BackupSendError("no webhook")))

    with pytest.raises(dispatch.NotifyError):
        dispatch.notify("hello")
