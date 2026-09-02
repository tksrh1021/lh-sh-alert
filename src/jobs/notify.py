"""매칭 결과 중 아직 안 보낸 것만 카카오톡으로 발송.
python -m src.jobs.notify [--dry-run]

발송 규칙(설계서 7.4): 동일 공고는 1번만, quiet_hours 중이면 건너뛰고 다음 실행 때
자연스럽게 재시도(별도 큐 없이 '아직 notified 아님' 상태로 남겨두는 것으로 충분),
하루 최대 10건 초과 시 요약 1건으로 묶음.

접수 시작일이 한참 남은 공고는 발견 즉시 보내지 않고, 시작일 기준 3일 전부터
보낸다(주말이 껴 있으면 서류 준비 여유를 더 주려고 5일 전으로 늘림) — 사용자 요청.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from src.matcher import match
from src.notifier.dispatch import NotifyError, notify
from src.notifier.templates import build_notification
from src.profile import load_profile
from src.quiet_hours import is_quiet_now
from src.store import Store

DB_PATH = "data/notices.db"
DAILY_CAP = 10


def _lead_days(apply_start: date) -> int:
    for offset in (1, 2, 3):
        if (apply_start - timedelta(days=offset)).weekday() >= 5:  # 5=토, 6=일
            return 5
    return 3


def _ready_to_notify(notice, today: date) -> bool:
    """접수 시작일을 모르면(주로 LH) 그냥 알린다 — 판단할 근거가 없을 땐
    보류보다 알리는 쪽이 안전하다는 기존 원칙 그대로."""
    if notice.apply_start is None:
        return True
    days_until_start = (notice.apply_start - today).days
    if days_until_start < 0:  # 이미 접수 시작됨 -> 바로 알려야 함
        return True
    return days_until_start <= _lead_days(notice.apply_start)


def _profile_path() -> str:
    return "profile.yaml" if Path("profile.yaml").exists() else "profile.example.yaml"


def run(dry_run: bool = False, today: date | None = None) -> dict:
    today = today or date.today()
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    sent, skipped_quiet, skipped_already, skipped_not_ready, failed = [], [], [], [], []

    try:
        candidates = []
        for notice in store.all():
            if store.has_notified(notice.id, "new"):
                skipped_already.append(notice)
                continue
            result = match(notice, profile, today=today)
            if result.verdict not in ("MATCH", "NEEDS_REVIEW"):
                continue
            if not _ready_to_notify(notice, today):
                skipped_not_ready.append(notice)
                continue
            candidates.append((notice, result))

        if is_quiet_now(profile.notify.quiet_hours):
            return {
                "sent": [], "skipped_quiet": candidates, "skipped_already": skipped_already,
                "skipped_not_ready": skipped_not_ready, "failed": [],
            }

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

    return {
        "sent": sent, "skipped_quiet": skipped_quiet, "skipped_already": skipped_already,
        "skipped_not_ready": skipped_not_ready, "failed": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)
    mode = "[dry-run] " if args.dry_run else ""
    print(
        f"{mode}발송 {len(result['sent'])}건 / 이미 발송됨 {len(result['skipped_already'])}건 / "
        f"조용한시간 보류 {len(result['skipped_quiet'])}건 / "
        f"접수시작 대기 {len(result['skipped_not_ready'])}건 / 실패 {len(result['failed'])}건"
    )
    for notice, _ in result["sent"]:
        print(f"  [SENT] [{notice.source}] {notice.title}")
    for notice, error in result["failed"]:
        print(f"  [FAILED] [{notice.source}] {notice.title} -> {error}")


if __name__ == "__main__":
    main()
