"""접수 마감 D-3/D-1/D-0 리마인드. python -m src.jobs.remind
apply_end이 있는 공고만 대상 (Phase 1 기준 LH만 해당, SH는 상세 파싱 이후 지원).
"""
import argparse
from datetime import date
from pathlib import Path

from src.matcher import match
from src.notifier.dispatch import NotifyError, notify
from src.notifier.templates import build_reminder
from src.profile import load_profile
from src.store import Store

DB_PATH = "data/notices.db"


def _profile_path() -> str:
    return "profile.yaml" if Path("profile.yaml").exists() else "profile.example.yaml"


def run(today: date | None = None, dry_run: bool = False) -> dict:
    today = today or date.today()
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    sent, failed = [], []

    try:
        for notice in store.all():
            if not notice.apply_end:
                continue
            if match(notice, profile, today=today).verdict == "NO_MATCH":
                continue
            days_left = (notice.apply_end - today).days
            if days_left not in profile.notify.reminder_days_before:
                continue

            kind = f"reminder_d{days_left}"
            if store.has_notified(notice.id, kind):
                continue

            text, link = build_reminder(notice, days_left)
            if dry_run:
                sent.append((notice, days_left))
                continue
            try:
                channel = notify(text, link)
                store.record_notification(notice.id, kind, channel)
                sent.append((notice, days_left))
            except NotifyError as e:
                failed.append((notice, str(e)))
    finally:
        store.close()

    return {"sent": sent, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)
    mode = "[dry-run] " if args.dry_run else ""
    print(f"{mode}리마인드 발송 {len(result['sent'])}건 / 실패 {len(result['failed'])}건")
    for notice, days_left in result["sent"]:
        print(f"  [D-{days_left}] [{notice.source}] {notice.title}")


if __name__ == "__main__":
    main()
