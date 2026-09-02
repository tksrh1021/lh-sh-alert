"""매칭 결과 중 아직 안 보낸 것만 카카오톡으로 발송.
python -m src.jobs.notify [--dry-run]

발송 규칙(설계서 7.4): 동일 공고는 1번만, quiet_hours 중이면 건너뛰고 다음 실행 때
자연스럽게 재시도(별도 큐 없이 '아직 notified 아님' 상태로 남겨두는 것으로 충분),
하루 최대 10건 초과 시 요약 1건으로 묶음.
"""
import argparse
from pathlib import Path

from src.matcher import match
from src.notifier.dispatch import NotifyError, notify
from src.notifier.templates import build_notification
from src.profile import load_profile
from src.quiet_hours import is_quiet_now
from src.store import Store

DB_PATH = "data/notices.db"
DAILY_CAP = 10


def _profile_path() -> str:
    return "profile.yaml" if Path("profile.yaml").exists() else "profile.example.yaml"


def run(dry_run: bool = False) -> dict:
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    sent, skipped_quiet, skipped_already, failed = [], [], [], []

    try:
        candidates = []
        for notice in store.all():
            if store.has_notified(notice.id, "new"):
                skipped_already.append(notice)
                continue
            result = match(notice, profile)
            if result.verdict in ("MATCH", "NEEDS_REVIEW"):
                candidates.append((notice, result))

        if is_quiet_now(profile.notify.quiet_hours):
            return {"sent": [], "skipped_quiet": candidates, "skipped_already": skipped_already, "failed": []}

        if len(candidates) > DAILY_CAP:
            titles = "\n".join(f"· [{n.source}] {n.title}" for n, _ in candidates)
            text = f"📋 오늘 확인할 공고가 {len(candidates)}건이라 요약해서 보내요\n\n{titles}"
            if not dry_run:
                channel = notify(text)
                for notice, _ in candidates:
                    store.record_notification(notice.id, "new", channel)
            sent = candidates
        else:
            for notice, result in candidates:
                text, link = build_notification(notice, result)
                if dry_run:
                    sent.append((notice, result))
                    continue
                try:
                    channel = notify(text, link)
                    store.record_notification(notice.id, "new", channel)
                    sent.append((notice, result))
                except NotifyError as e:
                    failed.append((notice, str(e)))
    finally:
        store.close()

    return {"sent": sent, "skipped_quiet": skipped_quiet, "skipped_already": skipped_already, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)
    mode = "[dry-run] " if args.dry_run else ""
    print(
        f"{mode}발송 {len(result['sent'])}건 / 이미 발송됨 {len(result['skipped_already'])}건 / "
        f"조용한시간 보류 {len(result['skipped_quiet'])}건 / 실패 {len(result['failed'])}건"
    )
    for notice, _ in result["sent"]:
        print(f"  [SENT] [{notice.source}] {notice.title}")
    for notice, error in result["failed"]:
        print(f"  [FAILED] [{notice.source}] {notice.title} -> {error}")


if __name__ == "__main__":
    main()
