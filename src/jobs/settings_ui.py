"""로컬에서 여는 필터 설정 화면. profile.yaml을 만들어주고, 저장하면
GitHub Actions가 볼 수 있도록 GitHub Secret(PROFILE_YAML)까지 자동으로 갱신한다.

실행: python -m src.jobs.settings_ui
"""
import http.server
import urllib.parse
import webbrowser
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.github_secrets import GithubSecretError, set_secret
from src.profile import Profile

PORT = 8766
PROFILE_PATH = Path("profile.yaml")
EXAMPLE_PATH = Path("profile.example.yaml")


def _load_current() -> dict:
    path = PROFILE_PATH if PROFILE_PATH.exists() else EXAMPLE_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _split_csv(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _render_form(data: dict, message: str = "") -> str:
    personal = data.get("personal", {})
    assets = data.get("assets", {})
    interests = data.get("interests", {})
    notify = data.get("notify", {})

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>공공임대 알림 봇 - 필터 설정</title>
<style>
body {{ font-family: sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }}
label {{ display: block; margin-top: 16px; font-weight: bold; }}
input {{ width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; }}
small {{ color: #666; }}
button {{ margin-top: 24px; padding: 10px 20px; font-size: 16px; }}
.msg {{ padding: 12px; margin-bottom: 16px; border-radius: 4px; }}
.ok {{ background: #e6ffed; }}
.err {{ background: #ffeef0; }}
</style></head>
<body>
<h2>내 조건 설정</h2>
{f'<div class="msg {"err" if "실패" in message else "ok"}">{message}</div>' if message else ""}
<form method="post" action="/save">
  <label>생년월일</label>
  <input type="date" name="birth_date" value="{personal.get('birth_date', '')}" required>

  <label>총자산 (원)</label>
  <input type="number" name="total_asset_krw" value="{assets.get('total_asset_krw', 0)}">

  <label>차량가액 (원)</label>
  <input type="number" name="car_value_krw" value="{assets.get('car_value_krw', 0)}">

  <label>관심 주택 유형 (쉼표로 구분)</label>
  <input type="text" name="housing_types" value="{', '.join(interests.get('housing_types', []))}">
  <small>예: 행복주택, 청년매입임대, 청년전세임대, 청년안심주택</small>

  <label>관심 대상 계층 (쉼표로 구분)</label>
  <input type="text" name="target_groups" value="{', '.join(interests.get('target_groups', []))}">
  <small>예: 청년, 신혼부부, 고령자</small>

  <label>관심 지역 - 시/도 (쉼표로 구분)</label>
  <input type="text" name="regions" value="{', '.join(interests.get('regions', []))}">
  <small>이 지역 공고만 옵니다. 예: 서울특별시, 경기도</small>

  <label>알림 금지 시간</label>
  <input type="text" name="quiet_hours" value="{notify.get('quiet_hours', '23:00-08:00')}">
  <small>이 시간엔 알림을 다음날 아침으로 미룹니다. 형식: 23:00-08:00</small>

  <button type="submit">저장 + GitHub에 반영</button>
</form>
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond(_render_form(_load_current()))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body)

        data = {
            "personal": {"birth_date": form.get("birth_date", [""])[0]},
            "assets": {
                "total_asset_krw": int(form.get("total_asset_krw", ["0"])[0] or 0),
                "car_value_krw": int(form.get("car_value_krw", ["0"])[0] or 0),
            },
            "interests": {
                "housing_types": _split_csv(form.get("housing_types", [""])[0]),
                "target_groups": _split_csv(form.get("target_groups", [""])[0]),
                "regions": _split_csv(form.get("regions", [""])[0]),
            },
            "notify": {"quiet_hours": form.get("quiet_hours", [""])[0] or None},
        }

        try:
            Profile(**data)  # 검증만, 실제 파일엔 date를 문자열로 그대로 저장
        except ValidationError as e:
            self._respond(_render_form(data, f"저장 실패: 입력값 확인 필요 ({e.errors()[0]['msg']})"))
            return

        yaml_text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        PROFILE_PATH.write_text(yaml_text, encoding="utf-8")

        try:
            set_secret("PROFILE_YAML", yaml_text)
            message = "저장 완료. GitHub Secret(PROFILE_YAML)도 갱신했습니다."
        except GithubSecretError as e:
            message = f"로컬엔 저장했지만 GitHub 반영 실패: {e}"

        self._respond(_render_form(data, message))

    def _respond(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main() -> None:
    url = f"http://127.0.0.1:{PORT}/"
    print(f"브라우저에서 열립니다: {url}  (Ctrl+C로 종료)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
