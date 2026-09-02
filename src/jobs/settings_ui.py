"""로컬에서 여는 필터 설정 화면. profile.yaml을 만들어주고, 저장하면
GitHub Actions가 볼 수 있도록 GitHub Secret(PROFILE_YAML)까지 자동으로 갱신한다.

실행: python -m src.jobs.settings_ui
"""
import html
import http.server
import urllib.parse
import webbrowser
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.config import HOUSING_TYPE_KEYWORDS, REGIONS, TARGET_GROUP_KEYWORDS
from src.github_secrets import GithubSecretError, set_secret
from src.profile import Profile

PORT = 8766
PROFILE_PATH = Path("profile.yaml")
EXAMPLE_PATH = Path("profile.example.yaml")


def _load_current() -> dict:
    path = PROFILE_PATH if PROFILE_PATH.exists() else EXAMPLE_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _chips(field_name: str, options: list[str], selected: list[str]) -> str:
    items = []
    for opt in options:
        checked = "checked" if opt in selected else ""
        opt_esc = html.escape(opt)
        items.append(
            f'<label class="chip"><input type="checkbox" name="{field_name}" value="{opt_esc}" {checked}>'
            f'<span>{opt_esc}</span></label>'
        )
    return "\n".join(items)


def _render_form(data: dict, message: str = "") -> str:
    personal = data.get("personal", {})
    assets = data.get("assets", {})
    interests = data.get("interests", {})
    notify = data.get("notify", {})

    quiet_hours = notify.get("quiet_hours") or "23:00-08:00"
    quiet_start, quiet_end = (quiet_hours.split("-") + ["", ""])[:2]

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>공공임대 알림 봇 - 필터 설정</title>
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/wanteddev/wanted-sans@v1.0.3/webfonts/wanted-sans-cdn.css">
<style>
:root {{
  --wanted-blue: #3552e4;
  --wanted-blue-dark: #2a41b8;
  --ink: #17171c;
  --sub: #6c6c75;
  --line: #e8e8ee;
  --bg: #f4f5f9;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "Wanted Sans", -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: var(--bg); color: var(--ink);
  max-width: 560px; margin: 48px auto; padding: 0 16px;
}}
.card {{
  background: #fff; border-radius: 20px; padding: 32px 28px;
  box-shadow: 0 4px 24px rgba(23, 23, 28, 0.06);
}}
h2 {{ font-size: 22px; font-weight: 800; margin: 0 0 4px; }}
.sub {{ color: var(--sub); font-size: 14px; margin-bottom: 24px; }}
label.field-label {{ display: block; margin-top: 24px; font-weight: 700; font-size: 14px; }}
input[type=date], input[type=number], input[type=time] {{
  width: 100%; padding: 12px 14px; margin-top: 8px; box-sizing: border-box;
  border: 1.5px solid var(--line); border-radius: 10px; font-size: 15px;
  font-family: inherit; color: var(--ink);
}}
input[type=date]:focus, input[type=number]:focus, input[type=time]:focus {{
  outline: none; border-color: var(--wanted-blue);
}}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.chip {{ cursor: pointer; }}
.chip input {{ display: none; }}
.chip span {{
  display: inline-block; padding: 9px 16px; border-radius: 999px;
  border: 1.5px solid var(--line); font-size: 14px; font-weight: 600;
  color: var(--sub); transition: all .12s ease;
}}
.chip input:checked + span {{
  background: var(--wanted-blue); border-color: var(--wanted-blue); color: #fff;
}}
.time-row {{ display: flex; gap: 10px; align-items: center; margin-top: 8px; }}
.time-row span {{ color: var(--sub); }}
small.hint {{ display: block; color: var(--sub); font-size: 12px; margin-top: 6px; }}
button {{
  width: 100%; margin-top: 32px; padding: 14px; font-size: 16px; font-weight: 800;
  color: #fff; background: var(--wanted-blue); border: none; border-radius: 12px;
  cursor: pointer; font-family: inherit;
}}
button:hover {{ background: var(--wanted-blue-dark); }}
.msg {{ padding: 14px 16px; margin-bottom: 20px; border-radius: 10px; font-size: 14px; font-weight: 600; }}
.ok {{ background: #eaf0ff; color: var(--wanted-blue-dark); }}
.err {{ background: #fdecec; color: #c62828; }}
</style></head>
<body>
<div class="card">
  <h2>내 조건 설정</h2>
  <p class="sub">여기서 정한 조건에 맞는 공고만 카카오톡으로 옵니다</p>
  {f'<div class="msg {"err" if "실패" in message else "ok"}">{message}</div>' if message else ""}
  <form method="post" action="/save">
    <label class="field-label">생년월일</label>
    <input type="date" name="birth_date" value="{personal.get('birth_date', '')}" required>

    <label class="field-label">총자산 (원)</label>
    <input type="number" name="total_asset_krw" value="{assets.get('total_asset_krw', 0)}">

    <label class="field-label">차량가액 (원)</label>
    <input type="number" name="car_value_krw" value="{assets.get('car_value_krw', 0)}">

    <label class="field-label">관심 주택 유형</label>
    <div class="chips">{_chips("housing_types", HOUSING_TYPE_KEYWORDS, interests.get('housing_types', []))}</div>

    <label class="field-label">관심 대상 계층</label>
    <div class="chips">{_chips("target_groups", TARGET_GROUP_KEYWORDS, interests.get('target_groups', []))}</div>

    <label class="field-label">관심 지역</label>
    <small class="hint">아무것도 선택 안 하면 전체 지역을 봅니다</small>
    <div class="chips">{_chips("regions", REGIONS, interests.get('regions', []))}</div>

    <label class="field-label">알림 금지 시간</label>
    <div class="time-row">
      <input type="time" name="quiet_start" value="{quiet_start}">
      <span>~</span>
      <input type="time" name="quiet_end" value="{quiet_end}">
    </div>
    <small class="hint">이 시간엔 알림을 다음날 아침으로 미룹니다</small>

    <button type="submit">저장하고 GitHub에 반영</button>
  </form>
</div>
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond(_render_form(_load_current()))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body)

        quiet_start = form.get("quiet_start", [""])[0]
        quiet_end = form.get("quiet_end", [""])[0]
        quiet_hours = f"{quiet_start}-{quiet_end}" if quiet_start and quiet_end else None

        data = {
            "personal": {"birth_date": form.get("birth_date", [""])[0]},
            "assets": {
                "total_asset_krw": int(form.get("total_asset_krw", ["0"])[0] or 0),
                "car_value_krw": int(form.get("car_value_krw", ["0"])[0] or 0),
            },
            "interests": {
                "housing_types": form.get("housing_types", []),
                "target_groups": form.get("target_groups", []),
                "regions": form.get("regions", []),
            },
            "notify": {"quiet_hours": quiet_hours},
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

    def _respond(self, html_body: str):
        body = html_body.encode("utf-8")
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
