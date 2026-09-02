"""카카오 '나에게 보내기'. access_token은 수명이 짧아서 매번 refresh_token으로 새로 받는다."""
import json

import httpx

from src.env import load_env, save_env

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


class KakaoSendError(Exception):
    pass


def _refresh_access_token(env: dict) -> str:
    rest_key = env.get("KAKAO_REST_API_KEY")
    refresh_token = env.get("KAKAO_REFRESH_TOKEN")
    if not rest_key or not refresh_token:
        raise KakaoSendError("KAKAO_REST_API_KEY 또는 KAKAO_REFRESH_TOKEN이 .env에 없음")

    data = {"grant_type": "refresh_token", "client_id": rest_key, "refresh_token": refresh_token}
    client_secret = env.get("KAKAO_CLIENT_SECRET")
    if client_secret:
        data["client_secret"] = client_secret

    resp = httpx.post(TOKEN_URL, data=data, timeout=15)
    body = resp.json()
    if "access_token" not in body:
        raise KakaoSendError(f"토큰 갱신 실패: {json.dumps(body, ensure_ascii=False)}")

    if "refresh_token" in body:  # 카카오가 새 refresh_token을 주면 교체
        save_env({"KAKAO_REFRESH_TOKEN": body["refresh_token"]})

    return body["access_token"]


def send_kakao(text: str, link_url: str | None = None) -> None:
    env = load_env()
    access_token = _refresh_access_token(env)

    template = {"object_type": "text", "text": text}
    if link_url:
        template["link"] = {"web_url": link_url, "mobile_web_url": link_url}

    resp = httpx.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=15,
    )
    body = resp.json()
    if body.get("result_code") != 0:
        raise KakaoSendError(f"발송 실패: {json.dumps(body, ensure_ascii=False)}")
