"""GitHub Actions Secret을 로컬에서 갱신한다.

profile.yaml은 소득 시절엔 민감정보라 커밋을 안 했는데, 그러면 서버(Actions)가
이 파일을 아예 못 본다. 그래서 UI에서 프로필을 저장하면 이 모듈이 GitHub가
요구하는 방식(리포의 공개키로 libsodium sealed box 암호화)으로 감싸서
Secret으로 올린다 — 저장소에는 암호화된 값만 남고, 원문은 GitHub도 못 본다.
"""
import base64

import httpx
from nacl import encoding, public

from src.env import load_env

API_BASE = "https://api.github.com"


class GithubSecretError(Exception):
    pass


def _encrypt(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def set_secret(secret_name: str, value: str) -> None:
    env = load_env()
    token = env.get("GITHUB_PAT")
    repo = env.get("GITHUB_REPO")
    if not token or not repo:
        raise GithubSecretError("GITHUB_PAT / GITHUB_REPO가 .env에 없음")

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    key_resp = httpx.get(f"{API_BASE}/repos/{repo}/actions/secrets/public-key", headers=headers, timeout=15)
    if key_resp.status_code != 200:
        raise GithubSecretError(f"공개키 조회 실패: {key_resp.status_code} {key_resp.text}")
    key_data = key_resp.json()

    encrypted_value = _encrypt(key_data["key"], value)
    put_resp = httpx.put(
        f"{API_BASE}/repos/{repo}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
        timeout=15,
    )
    if put_resp.status_code not in (201, 204):
        raise GithubSecretError(f"시크릿 저장 실패: {put_resp.status_code} {put_resp.text}")
