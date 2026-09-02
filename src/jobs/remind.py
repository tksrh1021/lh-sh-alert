"""접수 시작일 1번 + 마감일 1번, 총 두 번만 리마인드한다. python -m src.jobs.remind
apply_start/apply_end이 있는 공고만 대상 (LH는 목록에 마감일만 있어 마감 리마인드만 나감,
SH는 상세 페이지에서 시작/마감 둘 다 뽑아와서 둘 다 나간다).
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
            if match(notice, profile, today=today).verdict == "NO_MATCH":
                continue

            for kind, target_date in (("start", notice.apply_start), ("end", notice.apply_end)):
                if target_date != today:
                    continue
                notification_kind = f"reminder_{kind}"
                if store.has_notified(notice.id, notification_kind):
                    continue

                text, link = build_reminder(notice, kind)
                if dry_run:
                    sent.append((notice, kind))
                    continue
                try:
                    channel = notify(text, link)
                    store.record_notification(notice.id, notification_kind, channel)
                    sent.append((notice, kind))
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
    for notice, kind in result["sent"]:
        label = "접수시작" if kind == "start" else "마감"
        print(f"  [{label}] [{notice.source}] {notice.title}")


if __name__ == "__main__":
    main()
