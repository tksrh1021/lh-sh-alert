from pathlib import Path

from src.collectors.sh_crawler import SHCrawler

FIXTURE = Path(__file__).parent / "fixtures" / "sh_list.html"
FIXTURE_PAGE2 = Path(__file__).parent / "fixtures" / "sh_list_page2.html"


def test_parse_rows_from_real_sample():
    html = FIXTURE.read_text(encoding="utf-8")
    rows = SHCrawler()._parse_rows(html)

    assert len(rows) >= 10  # 실측 시 14건
    row = rows[0]
    assert row["title"]
    assert row["seq"].isdigit()
    assert row["detail_url"].startswith("https://www.i-sh.co.kr")


def test_parse_rows_empty_html_returns_empty():
    rows = SHCrawler()._parse_rows("<html><body>no table here</body></html>")
    assert rows == []


def test_collect_fetches_two_pages_without_duplicates(monkeypatch):
    """1페이지만 보면 하루에 글이 많은 날 놓칠 수 있어 2페이지까지 본다.
    실제로 8/20 공고를 놓쳤던 사례를 보고 늘림."""
    page1_html = FIXTURE.read_text(encoding="utf-8")
    page2_html = FIXTURE_PAGE2.read_text(encoding="utf-8")

    crawler = SHCrawler()
    fetched_pages = []

    def fake_fetch_list(page=1):
        fetched_pages.append(page)
        return page1_html if page == 1 else page2_html

    monkeypatch.setattr(crawler, "_fetch_list", fake_fetch_list)
    monkeypatch.setattr(crawler, "_fetch_detail_text", lambda seq: None)
    monkeypatch.setattr("src.collectors.sh_crawler.time.sleep", lambda seconds: None)

    rows = crawler.collect()

    assert fetched_pages == [1, 2]
    seqs = [r["seq"] for r in rows]
    assert len(seqs) == len(set(seqs))  # 중복 없음
    page1_seqs = {r["seq"] for r in crawler._parse_rows(page1_html)}
    page2_seqs = {r["seq"] for r in crawler._parse_rows(page2_html)}
    assert page1_seqs | page2_seqs == set(seqs)
