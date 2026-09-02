"""Phase 0: SH 공고 상세 페이지 실측.

목록 페이지의 getDetailView(seq)는 mainform을 view.do로 POST함
(hidden fields: seq, multi_itm_seq=2, page). GET이 아니라 POST라는 게
핵심 발견이라 별도 스크립트로 확인한다.

실행: python research/probe_sh_detail.py <seq>
"""
import pathlib
import sys
import httpx
from bs4 import BeautifulSoup

BASE = "https://www.i-sh.co.kr/app/lay2/program/S48T1581C563/www/brd/m_247"
HEADERS = {"User-Agent": "lh-sh-alert-research/0.1 (personal notice checker)"}
SAMPLES_DIR = pathlib.Path(__file__).parent / "samples"


def fetch_detail(seq: str) -> str:
    resp = httpx.post(
        f"{BASE}/view.do",
        headers=HEADERS,
        data={"seq": seq, "multi_itm_seq": "2", "page": "1"},
        timeout=15,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


def summarize(html: str) -> None:
    soup = BeautifulSoup(html, "lxml")
    pdf_links = [a.get("href") for a in soup.select("a[href*='.pdf'], a[href*='download'], a[href*='fileDown']")]
    print(f"첨부/PDF 관련 링크 {len(pdf_links)}개:")
    for link in pdf_links[:10]:
        print(" -", link)
    body = soup.get_text(" ", strip=True)
    print(f"본문 텍스트 길이: {len(body)}자")
    print("본문 앞부분 미리보기:", body[:300])


def main() -> None:
    seq = sys.argv[1] if len(sys.argv) > 1 else "309497"
    html = fetch_detail(seq)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    out = SAMPLES_DIR / f"sh_detail_{seq}.html"
    out.write_text(html, encoding="utf-8")
    print(f"저장 완료: {out} ({len(html)} bytes)")
    summarize(html)


if __name__ == "__main__":
    main()
