"""Phase 0: SH 인터넷청약시스템 주택임대 공고 게시판 실측.

실행: python research/probe_sh.py
결과: research/samples/sh_list.html 저장 + 파싱 가능 여부를 표준출력에 요약.
"""
import pathlib
import httpx
from bs4 import BeautifulSoup

URL = "https://www.i-sh.co.kr/app/lay2/program/S48T1581C563/www/brd/m_247/list.do?multi_itm_seq=2"
HEADERS = {"User-Agent": "lh-sh-alert-research/0.1 (personal notice checker)"}

SAMPLES_DIR = pathlib.Path(__file__).parent / "samples"


def fetch() -> str:
    resp = httpx.get(URL, headers=HEADERS, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def summarize(html: str) -> None:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table tr")
    print(f"table tr 개수: {len(rows)}")
    if len(rows) <= 1:
        print("경고: 표 형태를 찾지 못했습니다. JS 렌더링 페이지일 가능성 있음 -> Playwright 검토 필요.")
        return
    print("첫 3행 텍스트 미리보기:")
    for row in rows[1:4]:
        cells = [c.get_text(strip=True) for c in row.select("td")]
        print(" |", cells)
    links = soup.select("table a[href]")
    print(f"게시판 내 링크 개수: {len(links)}")
    if links:
        print("첫 링크 예시:", links[0].get_text(strip=True), "->", links[0].get("href"))


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    html = fetch()
    out = SAMPLES_DIR / "sh_list.html"
    out.write_text(html, encoding="utf-8")
    print(f"저장 완료: {out} ({len(html)} bytes)")
    summarize(html)


if __name__ == "__main__":
    main()
