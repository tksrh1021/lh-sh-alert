from pathlib import Path

from src.collectors.sh_crawler import SHCrawler

FIXTURE = Path(__file__).parent / "fixtures" / "sh_list.html"


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
