from pathlib import Path

from src.collectors.lh_crawler import LHCrawler

FIXTURE = Path(__file__).parent / "fixtures" / "lh_list.html"


def test_parse_rows_from_real_sample():
    html = FIXTURE.read_text(encoding="utf-8")
    rows = LHCrawler()._parse_rows(html)

    assert len(rows) >= 40  # 실측 시 50건
    row = rows[0]
    assert row["housing_type"]
    assert row["region"]
    assert row["posted_at"]
    assert row["deadline"]
    assert row["status"]
    assert row["pan_id"]


def test_parse_rows_empty_html_raises_no_error_but_returns_empty():
    rows = LHCrawler()._parse_rows("<html><body>no table here</body></html>")
    assert rows == []
