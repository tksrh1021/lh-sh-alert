"""Phase 0: 카카오 로그인 OAuth 인증 + '나에게 보내기' 테스트.

로컬에 127.0.0.1:8765로 콜백을 받는 서버를 띄우고,
브라우저에서 인증 URL을 열어 로그인/동의하면 access_token + refresh_token을 받는다.
받은 즉시 talk_message API로 테스트 메시지를 스스로에게 보낸다.

사전 조건: Kakao Developers 앱에서
  - "카카오 로그인" 활성화
  - Redirect URI에 http://127.0.0.1:8765/callback 등록
  - 동의항목에 "카카오톡 메시지 전송" 켜짐
이 안 되어 있으면 브라우저에서 에러 코드(KOE101, KOE006 등)가 뜨는데,
그 에러 코드를 보고 무엇을 고쳐야 하는지 알 수 있다.

실행: python research/kakao_oauth.py
"""
import http.server
import json
import os
import pathlib
import threading
import urllib.parse
import webbrowser

import httpx

REDIRECT_URI = "http://127.0.0.1:8765/callback"
AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

ROOT = pathlib.Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"

received_code = {}


def load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(updates: dict) -> None:
    env = load_env()
    env.update(updates)
    lines = [f"{k}={v}" for k, v in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if "code" in qs:
            received_code["code"] = qs["code"][0]
            self.wfile.write("<h1>인증 완료. 이 창은 닫으셔도 됩니다.</h1>".encode("utf-8"))
        else:
            received_code["error"] = qs.get("error", ["unknown"])[0]
            received_code["error_description"] = qs.get("error_description", [""])[0]
            self.wfile.write(f"<h1>에러: {received_code['error']}</h1>".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_server():
    server = http.server.HTTPServer(("127.0.0.1", 8765), CallbackHandler)
    while "code" not in received_code and "error" not in received_code:
        server.handle_request()


def main() -> None:
    env = load_env()
    rest_key = env.get("KAKAO_REST_API_KEY")
    if not rest_key:
        print("KAKAO_REST_API_KEY가 .env에 없습니다.")
        return

    auth_params = {
        "client_id": rest_key,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("아래 URL을 브라우저에서 열어 카카오 로그인 및 동의를 완료하세요:")
    print(auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    server_thread.join(timeout=180)

    if "error" in received_code:
        print(f"인증 실패: {received_code['error']} - {received_code.get('error_description')}")
        print("-> KOE006이면 Redirect URI 미등록, KOE101이면 앱 설정/카카오로그인 비활성화 문제일 가능성이 큽니다.")
        return
    if "code" not in received_code:
        print("타임아웃: 180초 안에 로그인이 완료되지 않았습니다.")
        return

    code = received_code["code"]
    token_data_req = {
        "grant_type": "authorization_code",
        "client_id": rest_key,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    client_secret = env.get("KAKAO_CLIENT_SECRET")
    if client_secret:
        token_data_req["client_secret"] = client_secret
    token_resp = httpx.post(TOKEN_URL, data=token_data_req, timeout=15)
    token_data = token_resp.json()
    if "access_token" not in token_data:
        print("토큰 발급 실패:", json.dumps(token_data, ensure_ascii=False, indent=2))
        return

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    print("토큰 발급 성공. access_token 길이:", len(access_token))

    if refresh_token:
        save_env({"KAKAO_REFRESH_TOKEN": refresh_token})
        print(".env에 KAKAO_REFRESH_TOKEN 저장 완료.")

    send_resp = httpx.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={
            "template_object": json.dumps(
                {
                    "object_type": "text",
                    "text": "🔧 lh-sh-alert 테스트 메시지 (Phase 0)",
                    "link": {"web_url": "https://www.i-sh.co.kr", "mobile_web_url": "https://www.i-sh.co.kr"},
                },
                ensure_ascii=False,
            )
        },
        timeout=15,
    )
    print("발송 결과:", send_resp.status_code, send_resp.text)


if __name__ == "__main__":
    main()
