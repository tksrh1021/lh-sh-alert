from src.jobs import collect as collect_job


class WorkingCrawler:
    def collect(self):
        return [
            {
                "no": "1", "housing_type": "행복주택", "title": "정상 공고", "region": "서울특별시",
                "has_attachment": False, "posted_at": "2026.01.01", "deadline": "2026.01.10",
                "status": "공고중", "pan_id": "1", "file_ids": None,
            }
        ]


class BrokenCrawler:
    def collect(self):
        raise RuntimeError("사이트 구조가 바뀐 것 같음")


def test_one_source_failing_does_not_block_the_other(tmp_path, monkeypatch):
    monkeypatch.setattr(collect_job, "LHCrawler", WorkingCrawler)
    monkeypatch.setattr(collect_job, "SHCrawler", BrokenCrawler)
    monkeypatch.setattr(collect_job, "DB_PATH", tmp_path / "notices.db")

    alerts = []
    monkeypatch.setattr(collect_job, "notify", lambda text, link=None: alerts.append(text) or "kakao")

    result = collect_job.run()

    assert len(result["new"]) == 1  # LH는 정상 수집됨
    assert len(result["errors"]) == 1
    assert "SH" in result["errors"][0]
    assert len(alerts) == 1  # 에러 알림이 나감
    assert "SH" in alerts[0]


def test_dry_run_does_not_alert_on_error(tmp_path, monkeypatch):
    monkeypatch.setattr(collect_job, "LHCrawler", WorkingCrawler)
    monkeypatch.setattr(collect_job, "SHCrawler", BrokenCrawler)
    monkeypatch.setattr(collect_job, "DB_PATH", tmp_path / "notices.db")

    monkeypatch.setattr(collect_job, "notify", lambda text, link=None: (_ for _ in ()).throw(AssertionError("dry-run에선 호출되면 안 됨")))

    result = collect_job.run(dry_run=True)
    assert len(result["errors"]) == 1
