"""마감이 확실히 지난 공고를 DB에서 지운다. python -m src.jobs.cleanup [--dry-run]

apply_end를 아는 경우만 지운다 — 모르는 공고는(마감일 미확인) 나중에 조건이
바뀌면 재평가될 수 있어서 함부로 안 지운다. 알림 이력(notifications)도
같이 지워서 나중에 우연히 같은 id가 재등장해도 꼬이지 않게 한다.
"""
import argparse
from datetime import date

from src.store import Store

DB_PATH = "data/notices.db"


def run(today: date | None = None, dry_run: bool = False) -> list:
    today = today or date.today()
    store = Store(DB_PATH)
    try:
        expired = [
            n for n in store.all()
            if n.apply_end is not None and n.apply_end < today
        ]
        if not dry_run:
            for notice in expired:
                store.delete(notice.id)
        return expired
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    expired = run(dry_run=args.dry_run)
    mode = "[dry-run] " if args.dry_run else ""
    print(f"{mode}삭제 대상 {len(expired)}건")
    for notice in expired:
        print(f"  [{notice.source}] {notice.title} (마감: {notice.apply_end.isoformat()})")


if __name__ == "__main__":
    main()
