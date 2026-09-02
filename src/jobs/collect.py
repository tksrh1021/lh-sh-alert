"""공고 수집 잡. python -m src.jobs.collect [--dry-run]
LH/SH 중 한쪽 사이트 구조가 바뀌어 깨져도 나머지 한쪽은 계속 수집한다.
"""
import argparse

from src.collectors.lh_crawler import LHCrawler
from src.collectors.sh_crawler import SHCrawler
from src.normalizer import normalize_lh, normalize_sh
from src.notifier.dispatch import NotifyError, notify
from src.notifier.templates import build_error_notice
from src.store import Store

DB_PATH = "data/notices.db"


def _collect_source(source: str, crawler, normalize) -> tuple[list, str | None]:
    try:
        rows = crawler().collect()
        return [normalize(r) for r in rows], None
    except Exception as e:  # 사이트 구조 변경 등 — 조용히 넘기지 않고 어느 소스가 죽었는지 기록
        return [], f"{source} 수집 실패: {e}"


def run(dry_run: bool = False) -> dict:
    lh_notices, lh_error = _collect_source("LH", LHCrawler, normalize_lh)
    sh_notices, sh_error = _collect_source("SH", SHCrawler, normalize_sh)
    notices = lh_notices + sh_notices
    errors = [e for e in (lh_error, sh_error) if e]

    store = Store(DB_PATH)
    counts = {"new": [], "changed": [], "unchanged": []}
    try:
        for notice in notices:
            if dry_run:
                existing = store.get(notice.id)
                if existing is None:
                    status = "new"
                elif existing.content_hash != notice.content_hash:
                    status = "changed"
                else:
                    status = "unchanged"
            else:
                status = store.upsert(notice)
            counts[status].append(notice)
    finally:
        store.close()

    if errors and not dry_run:
        for error in errors:
            try:
                notify(build_error_notice("collect", error))
            except NotifyError:
                pass  # 알림 채널까지 죽었으면 GitHub Actions 실행 로그가 마지막 보루

    return {**counts, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 미리 본다")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)

    mode = "[dry-run] " if args.dry_run else ""
    print(f"{mode}신규 {len(result['new'])}건 / 변경 {len(result['changed'])}건 / 동일 {len(result['unchanged'])}건")
    for notice in result["new"]:
        print(f"  [NEW][{notice.source}] {notice.title}")
    for notice in result["changed"]:
        print(f"  [CHANGED][{notice.source}] {notice.title}")
    for error in result["errors"]:
        print(f"  [ERROR] {error}")

    if result["errors"]:
        raise SystemExit(1)  # GitHub Actions 실행 목록에서 실패로 표시되게


if __name__ == "__main__":
    main()
