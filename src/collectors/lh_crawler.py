"""LH청약플러스 임대주택 공고 목록 크롤러.

research/probe_lh.py에서 실측 검증한 구조 그대로 사용.
PDF는 여기서 받지 않는다 — 공고 50건마다 매번 첨부파일까지 내려받으면
LH 서버에 불필요하게 요청이 많아진다. PDF가 필요해지는 시점(Phase 4,
매칭된 공고만)에 file_ids로 그때 받는다.
"""
import httpx
from bs4 import BeautifulSoup

from src.config import LH_LIST_URL, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}


class LHCrawler:
    def collect(self) -> list[dict]:
        html = self._fetch_list()
        return self._parse_rows(html)

    def _fetch_list(self) -> str:
        resp = httpx.get(LH_LIST_URL, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    def _parse_rows(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        rows = []
        for tr in soup.select("table tbody tr"):
            cells = [c.get_text(strip=True) for c in tr.select("td")]
            if len(cells) < 8:
                continue
            title_a = tr.select_one("a.wrtancInfoBtn")
            file_a = tr.select_one("a.listFileDown")
            if title_a is None:
                continue
            rows.append(
                {
                    "no": cells[0],
                    "housing_type": cells[1],
                    "title": cells[2],
                    "region": cells[3],
                    "has_attachment": "있음" in cells[4],
                    "posted_at": cells[5],
                    "deadline": cells[6],
                    "status": cells[7],
                    "pan_id": title_a.get("data-id1"),
                    "file_ids": (
                        {
                            "uppAisTpCd": file_a.get("data-id1"),
                            "aisTpCd": file_a.get("data-id2"),
                            "ccrCnntSysDsCd": file_a.get("data-id3"),
                            "lsSst": file_a.get("data-id4"),
                            "panId": file_a.get("data-id5"),
                        }
                        if file_a
                        else None
                    ),
                }
            )
        return rows
