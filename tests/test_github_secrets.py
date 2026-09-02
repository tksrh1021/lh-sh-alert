import base64

import httpx
import pytest
from nacl import encoding, public

from src import github_secrets


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data


def test_missing_env_raises(monkeypatch):
    monkeypatch.setattr(github_secrets, "load_env", lambda: {})
    with pytest.raises(github_secrets.GithubSecretError):
        github_secrets.set_secret("PROFILE_YAML", "personal:\n  birth_date: 1995-01-01\n")


def test_set_secret_success(monkeypatch):
    monkeypatch.setattr(
        github_secrets, "load_env", lambda: {"GITHUB_PAT": "token", "GITHUB_REPO": "user/repo"}
    )

    real_public_key = public.PrivateKey.generate().public_key
    public_key_b64 = real_public_key.encode(encoding.Base64Encoder()).decode("utf-8")

    calls = []

    def fake_get(url, **kwargs):
        calls.append(("GET", url))
        return FakeResponse(200, {"key": public_key_b64, "key_id": "key-123"})

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs.get("json")))
        return FakeResponse(201, {})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "put", fake_put)

    github_secrets.set_secret("PROFILE_YAML", "personal:\n  birth_date: 1995-01-01\n")

    assert calls[0] == ("GET", "https://api.github.com/repos/user/repo/actions/secrets/public-key")
    put_call = calls[1]
    assert put_call[1] == "https://api.github.com/repos/user/repo/actions/secrets/PROFILE_YAML"
    assert put_call[2]["key_id"] == "key-123"
    assert base64.b64decode(put_call[2]["encrypted_value"])  # 유효한 base64인지만 확인


def test_set_secret_raises_when_put_fails(monkeypatch):
    monkeypatch.setattr(
        github_secrets, "load_env", lambda: {"GITHUB_PAT": "token", "GITHUB_REPO": "user/repo"}
    )
    real_public_key = public.PrivateKey.generate().public_key
    public_key_b64 = real_public_key.encode(encoding.Base64Encoder()).decode("utf-8")

    monkeypatch.setattr(httpx, "get", lambda url, **kw: FakeResponse(200, {"key": public_key_b64, "key_id": "k"}))
    monkeypatch.setattr(httpx, "put", lambda url, **kw: FakeResponse(403, {"message": "no access"}))

    with pytest.raises(github_secrets.GithubSecretError):
        github_secrets.set_secret("PROFILE_YAML", "x")
