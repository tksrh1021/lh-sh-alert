"""profile.yaml의 quiet_hours("23:00-08:00") 문자열 판정. 자정을 넘나드는 구간도 처리한다."""
from datetime import datetime, time


def is_quiet_now(quiet_hours: str | None, now: time | None = None) -> bool:
    if not quiet_hours:
        return False
    now = now if now is not None else datetime.now().time()
    start_s, end_s = quiet_hours.split("-")
    start = time.fromisoformat(start_s.strip())
    end = time.fromisoformat(end_s.strip())

    if start <= end:
        return start <= now < end
    return now >= start or now < end  # 자정을 넘는 구간 (예: 23:00-08:00)
