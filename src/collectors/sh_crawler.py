"""SH 인터넷청약시스템 주택임대 공고 게시판 크롤러.

research/probe_sh.py, probe_sh_detail.py에서 실측 검증한 구조 사용.
목록은 GET, 상세보기는 JS로는 POST 폼 제출이지만 실측 결과 GET 쿼리스트링으로도
동일하게 열리는 걸 확인했음 (사람이 클릭할 원문 링크로 그대로 써도 됨).
"""
import re
import time

import httpx
from bs4 import BeautifulSoup

from src.config import REQUEST_DELAY_SECONDS, SH_DETAIL_URL, SH_LIST_URL, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}
SEQ_PATTERN = re.compile(r"getDetailView\('(\d+)'\)")
LIST_PAGES = 2  # 1페이지(~10건)만 보면 하루에 글이 많이 올라오는 날 놓칠 수 있어 2페이지까지 확인


class SHCrawler:
    def collect(self, pages: int | None = None) -> list[dict]:
        pages = pages or LIST_PAGES
        rows = []
        seen_seqs = set()
        for page in range(1, pages + 1):
            html = self._fetch_list(page)
            for row in self._parse_rows(html):
                if row["seq"] in seen_seqs:  # 페이지 사이에 새 글이 끼어들어 중복 노출되는 경우 방지
                    continue
                seen_seqs.add(row["seq"])
                rows.append(row)
            if page < pages:
                time.sleep(REQUEST_DELAY_SECONDS)

        for row in rows:
            row["detail_text"] = self._fetch_detail_text(row["seq"])
            time.sleep(REQUEST_DELAY_SECONDS)
        return rows

    def _fetch_list(self, page: int = 1) -> str:
        # httpx의 params는 URL에 이미 있는 쿼리스트링을 통째로 대체하므로
        # multi_itm_seq을 여기서 같이 안 넣으면 다른 게시판이 응답으로 온다.
        resp = httpx.get(
            SH_LIST_URL, params={"multi_itm_seq": "2", "page": page},
            headers=HEADERS, timeout=15, follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    def _fetch_detail_text(self, seq: str) -> str | None:
        """상세 페이지 본문 전체 텍스트. 접수 일정 문구 위치/표현이 공고마다 달라서
        (예: '청약신청 일정' vs '공급일정 > 청약신청 :') 어디를 찾을지는 normalizer가 판단한다."""
        try:
            resp = httpx.get(
                SH_DETAIL_URL, params={"seq": seq, "multi_itm_seq": "2"}, headers=HEADERS, timeout=15
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            return None
        return BeautifulSoup(resp.text, "lxml").get_text("\n", strip=True)

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
