"""SH 인터넷청약시스템 주택임대 공고 게시판 크롤러.

research/probe_sh.py, probe_sh_detail.py에서 실측 검증한 구조 사용.
목록은 GET, 상세보기는 JS로는 POST 폼 제출이지만 실측 결과 GET 쿼리스트링으로도
동일하게 열리는 걸 확인했음 (사람이 클릭할 원문 링크로 그대로 써도 됨).
"""
import re

import httpx
from bs4 import BeautifulSoup

from src.config import SH_DETAIL_URL, SH_LIST_URL, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}
SEQ_PATTERN = re.compile(r"getDetailView\('(\d+)'\)")


class SHCrawler:
    def collect(self) -> list[dict]:
        html = self._fetch_list()
        return self._parse_rows(html)

    def _fetch_list(self) -> str:
        resp = httpx.get(SH_LIST_URL, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    def _parse_rows(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows = []
        for tr in soup.select("table tbody tr, table tr"):
            cells = [c.get_text(strip=True) for c in tr.select("td")]
            if len(cells) < 5:
                continue
            link = tr.select_one("a[onclick*='getDetailView']")
            if link is None:
                continue
            match = SEQ_PATTERN.search(link.get("onclick", ""))
            if not match:
                continue
            seq = match.group(1)
            rows.append(
                {
                    "no": cells[0],
                    "title": cells[1],
                    "department": cells[2],
                    "posted_at": cells[3],
                    "views": cells[4],
                    "seq": seq,
                    "detail_url": f"{SH_DETAIL_URL}?seq={seq}&multi_itm_seq=2",
                }
            )
        return rows
