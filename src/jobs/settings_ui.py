"""로컬에서 여는 필터 설정 + 공고 캘린더 화면.

설정 화면에서 profile.yaml을 만들고 GitHub Secret(PROFILE_YAML)까지 자동 갱신한다.
캘린더 화면은 data/notices.db에 이미 모여있는 공고를 접수시작/마감일 기준으로
달력에 표시해서, LH 검색페이지(apply.lh.or.kr)처럼 날짜를 눌러 그날 공고를 본다.

실행: python -m src.jobs.settings_ui
"""
import calendar
import html
import http.server
import urllib.parse
import webbrowser
from datetime import date
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.config import HOUSING_TYPE_KEYWORDS, REGIONS, TARGET_GROUP_KEYWORDS
from src.github_secrets import GithubSecretError, set_secret
from src.matcher import match
from src.profile import Profile, load_profile
from src.store import Store

PORT = 8766
PROFILE_PATH = Path("profile.yaml")
EXAMPLE_PATH = Path("profile.example.yaml")
DB_PATH = "data/notices.db"

_BASE_CSS = """
:root {
  --wanted-blue: #3552e4; --wanted-blue-dark: #2a41b8;
  --ink: #17171c; --sub: #6c6c75; --line: #e8e8ee; --bg: #f4f5f9;
}
* { box-sizing: border-box; }
body {
  font-family: "Wanted Sans", -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: var(--bg); color: var(--ink); margin: 0; padding: 0 16px;
}
.wrap { max-width: 640px; margin: 0 auto; padding: 32px 0 60px; }
.tabs { display: flex; gap: 8px; margin-bottom: 20px; }
.tabs a {
  text-decoration: none; padding: 10px 18px; border-radius: 999px; font-weight: 700;
  font-size: 14px; color: var(--sub); background: #fff; border: 1.5px solid var(--line);
}
.tabs a.active { background: var(--wanted-blue); color: #fff; border-color: var(--wanted-blue); }
.card { background: #fff; border-radius: 20px; padding: 32px 28px; box-shadow: 0 4px 24px rgba(23,23,28,.06); }
h2 { font-size: 22px; font-weight: 800; margin: 0 0 4px; }
.sub { color: var(--sub); font-size: 14px; margin-bottom: 24px; }
label.field-label { display: block; margin-top: 24px; font-weight: 700; font-size: 14px; }
input[type=date], input[type=time] {
  width: 100%; padding: 12px 14px; margin-top: 8px; border: 1.5px solid var(--line);
  border-radius: 10px; font-size: 15px; font-family: inherit; color: var(--ink);
}
input:focus { outline: none; border-color: var(--wanted-blue); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.chip { cursor: pointer; }
.chip input { display: none; }
.chip span {
  display: inline-block; padding: 9px 16px; border-radius: 999px; border: 1.5px solid var(--line);
  font-size: 14px; font-weight: 600; color: var(--sub); transition: all .12s ease;
}
.chip input:checked + span { background: var(--wanted-blue); border-color: var(--wanted-blue); color: #fff; }
.time-row { display: flex; gap: 10px; align-items: center; margin-top: 8px; }
.time-row span { color: var(--sub); }
small.hint { display: block; color: var(--sub); font-size: 12px; margin-top: 6px; }
button {
  width: 100%; margin-top: 32px; padding: 14px; font-size: 16px; font-weight: 800;
  color: #fff; background: var(--wanted-blue); border: none; border-radius: 12px;
  cursor: pointer; font-family: inherit;
}
button:hover { background: var(--wanted-blue-dark); }
.msg { padding: 14px 16px; margin-bottom: 20px; border-radius: 10px; font-size: 14px; font-weight: 600; }
.ok { background: #eaf0ff; color: var(--wanted-blue-dark); }
.err { background: #fdecec; color: #c62828; }
table.cal { width: 100%; border-collapse: collapse; margin-top: 8px; }
table.cal th { padding: 8px 0; font-size: 12px; color: var(--sub); font-weight: 700; }
table.cal td {
  height: 68px; vertical-align: top; border: 1px solid var(--line); padding: 6px;
  font-size: 13px; color: var(--sub); position: relative;
}
table.cal td.other-month { color: #d5d5db; }
table.cal td a.daylink { color: var(--ink); text-decoration: none; font-weight: 700; }
.dot {
  display: block; margin-top: 4px; font-size: 11px; font-weight: 700; color: #fff;
  background: var(--wanted-blue); border-radius: 6px; padding: 2px 6px; text-align: center;
}
.cal-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.cal-nav a { color: var(--wanted-blue); text-decoration: none; font-weight: 700; }
.notice-item { padding: 14px 0; border-bottom: 1px solid var(--line); }
.notice-item:last-child { border-bottom: none; }
.notice-item .tag {
  display: inline-block; font-size: 11px; font-weight: 700; color: var(--wanted-blue);
  background: #eaf0ff; border-radius: 6px; padding: 2px 8px; margin-right: 6px;
}
.notice-item .tag.no-match { color: var(--sub); background: #f0f0f3; }
.notice-item .tag.match { color: #fff; background: var(--wanted-blue); }
.notice-item .tag.sent { color: #1a7f37; background: #e6f6ea; }
.notice-item a { color: var(--ink); font-weight: 700; text-decoration: none; }
.notice-item .meta { color: var(--sub); font-size: 13px; margin-top: 6px; }
.notice-item .reasons { color: var(--sub); font-size: 12px; margin-top: 6px; line-height: 1.6; }
.back-link { display: inline-block; margin-bottom: 16px; color: var(--sub); text-decoration: none; font-size: 14px; }
.filter-row { display: flex; gap: 8px; margin-bottom: 20px; }
.filter-row a {
  text-decoration: none; padding: 8px 14px; border-radius: 999px; font-weight: 700;
  font-size: 13px; color: var(--wanted-blue); background: #eaf0ff;
}
"""


def _page(title: str, active: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/wanteddev/wanted-sans@v1.0.3/webfonts/wanted-sans-cdn.css">
<style>{_BASE_CSS}</style></head>
<body><div class="wrap">
<div class="tabs">
  <a href="/" class="{'active' if active == 'settings' else ''}">필터 설정</a>
  <a href="/calendar" class="{'active' if active == 'calendar' else ''}">공고 캘린더</a>
  <a href="/dashboard" class="{'active' if active == 'dashboard' else ''}">대시보드</a>
</div>
{body}
</div></body></html>"""


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
    interests = data.get("interests", {})
    notify = data.get("notify", {})

    quiet_hours = notify.get("quiet_hours") or "23:00-08:00"
    quiet_start, quiet_end = (quiet_hours.split("-") + ["", ""])[:2]

    body = f"""
<div class="card">
  <h2>내 조건 설정</h2>
  <p class="sub">여기서 정한 조건에 맞는 공고만 카카오톡으로 옵니다</p>
  {f'<div class="msg {"err" if "실패" in message else "ok"}">{message}</div>' if message else ""}
  <form method="post" action="/save">
    <label class="field-label">생년월일</label>
    <input type="date" name="birth_date" value="{personal.get('birth_date', '')}" required>

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
</div>"""
    return _page("공공임대 알림 봇 - 필터 설정", "settings", body)


def _profile_path() -> str:
    return str(PROFILE_PATH) if PROFILE_PATH.exists() else str(EXAMPLE_PATH)


def _notices_by_date() -> dict[date, list[tuple[object, str]]]:
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    try:
        buckets: dict[date, list[tuple[object, str]]] = {}
        for notice in store.all():
            if match(notice, profile).verdict == "NO_MATCH":
                continue
            date_labels = (
                ("접수시작", notice.apply_start),
                ("접수마감", notice.apply_end),
                ("서류심사발표", notice.doc_review_date),
                ("당첨자발표", notice.result_date),
            )
            for label, d in date_labels:
                if d:
                    buckets.setdefault(d, []).append((notice, label))
        return buckets
    finally:
        store.close()


def _render_calendar(year: int, month: int) -> str:
    buckets = _notices_by_date()
    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdatescalendar(year, month)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    rows = []
    for week in weeks:
        cells = []
        for day in week:
            cls = "other-month" if day.month != month else ""
            count = len(buckets.get(day, []))
            badge = f'<a class="dot" href="/calendar/day?date={day.isoformat()}">{count}건</a>' if count else ""
            cells.append(
                f'<td class="{cls}"><a class="daylink" href="/calendar/day?date={day.isoformat()}">{day.day}</a>{badge}</td>'
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")

    body = f"""
<div class="card">
  <div class="cal-nav">
    <a href="/calendar?year={prev_year}&month={prev_month}">‹ 이전달</a>
    <h2>{year}년 {month}월</h2>
    <a href="/calendar?year={next_year}&month={next_month}">다음달 ›</a>
  </div>
  <p class="sub">내 조건에 맞는 공고의 접수시작/마감일이 표시됩니다</p>
  <table class="cal">
    <tr><th>일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th></tr>
    {''.join(rows)}
  </table>
</div>"""
    return _page("공공임대 알림 봇 - 공고 캘린더", "calendar", body)


def _render_day(target_date: date) -> str:
    buckets = _notices_by_date()
    items = buckets.get(target_date, [])

    if items:
        rows = []
        for notice, label in items:
            link = f'<a href="{notice.detail_url}" target="_blank">{html.escape(notice.title)}</a>' if notice.detail_url else html.escape(notice.title)
            rows.append(
                f'<div class="notice-item"><span class="tag">{label}</span>'
                f'<span class="tag">{notice.source}</span> {link}</div>'
            )
        list_html = "\n".join(rows)
    else:
        list_html = '<p class="sub">이 날짜엔 해당하는 공고가 없습니다.</p>'

    body = f"""
<div class="card">
  <a class="back-link" href="/calendar">‹ 캘린더로 돌아가기</a>
  <h2>{target_date.isoformat()}</h2>
  {list_html}
</div>"""
    return _page(f"{target_date.isoformat()} 공고", "calendar", body)


def _dashboard_rows(show_all: bool):
    """F-12 대시보드용 목록. 마감 임박한 순으로 정렬하고, 새 공고 알림이
    나갔는지(F-10 발송 이력)도 같이 보여준다."""
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    today = date.today()
    try:
        scored = []
        for notice in store.all():
            result = match(notice, profile)
            if result.verdict == "NO_MATCH" and not show_all:
                continue
            upcoming = [d for d in (notice.apply_start, notice.apply_end,
                                     notice.doc_review_date, notice.result_date) if d and d >= today]
            sort_key = min(upcoming) if upcoming else date.max
            sent = store.has_notified(notice.id, "new")
            scored.append((sort_key, notice, result, sent))
        scored.sort(key=lambda r: r[0])
        return [(n, r, s) for _, n, r, s in scored]
    finally:
        store.close()


def _render_dashboard(show_all: bool) -> str:
    rows = _dashboard_rows(show_all)

    items = []
    for notice, result, sent in rows:
        verdict_cls = "match" if result.verdict == "MATCH" else ("no-match" if result.verdict == "NO_MATCH" else "")
        link = (
            f'<a href="{notice.detail_url}" target="_blank">{html.escape(notice.title)}</a>'
            if notice.detail_url else html.escape(notice.title)
        )
        dates = []
        for label, d in (("접수", notice.apply_start), ("~", notice.apply_end),
                          ("서류심사", notice.doc_review_date), ("당첨발표", notice.result_date)):
            if d:
                dates.append(f"{label} {d.isoformat()}" if label != "~" else f"~ {d.isoformat()}")
        meta = " · ".join(filter(None, [notice.housing_type, ", ".join(notice.regions), " ".join(dates)]))
        reasons = "<br>".join(html.escape(r) for r in result.reasons) if result.reasons else ""

        items.append(f"""
<div class="notice-item">
  <span class="tag {verdict_cls}">{result.verdict}</span>
  <span class="tag">{notice.source}</span>
  {f'<span class="tag sent">발송됨</span>' if sent else ''}
  {link}
  <div class="meta">{html.escape(meta)}</div>
  {f'<div class="reasons">{reasons}</div>' if reasons else ''}
</div>""")

    list_html = "\n".join(items) if items else '<p class="sub">표시할 공고가 없습니다.</p>'
    toggle_href = "/dashboard" if show_all else "/dashboard?all=1"
    toggle_label = "관심 공고만 보기" if show_all else "부적합 포함 전체 보기"

    body = f"""
<div class="card">
  <h2>공고 대시보드</h2>
  <p class="sub">마감이 가까운 순으로 정렬됩니다</p>
  <div class="filter-row"><a href="{toggle_href}">{toggle_label}</a></div>
  {list_html}
</div>"""
    return _page("공공임대 알림 봇 - 대시보드", "dashboard", body)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/calendar":
            today = date.today()
            year = int(query.get("year", [today.year])[0])
            month = int(query.get("month", [today.month])[0])
            self._respond(_render_calendar(year, month))
        elif parsed.path == "/calendar/day":
            target = date.fromisoformat(query["date"][0])
            self._respond(_render_day(target))
        elif parsed.path == "/dashboard":
            show_all = query.get("all", ["0"])[0] == "1"
            self._respond(_render_dashboard(show_all))
        else:
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
