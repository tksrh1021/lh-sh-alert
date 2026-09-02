"""설계서 7.3절 메시지 포맷. Notice/MatchResult를 카카오톡에 보낼 텍스트로 바꾼다."""
from src.matcher import MatchResult
from src.models import Notice

VERDICT_EMOJI = {"MATCH": "🏠", "NEEDS_REVIEW": "🔎"}
VERDICT_LABEL = {"MATCH": "조건 맞는 공고 발견!", "NEEDS_REVIEW": "확인이 필요한 공고"}


def build_notification(notice: Notice, result: MatchResult) -> tuple[str, str | None]:
    emoji = VERDICT_EMOJI.get(result.verdict, "📌")
    label = VERDICT_LABEL.get(result.verdict, result.verdict)

    lines = [f"{emoji} {label}", "", f"[{notice.source}] {notice.title}"]
    if notice.housing_type:
        lines.append(f"· 유형: {notice.housing_type}")
    if notice.regions:
        lines.append(f"· 지역: {', '.join(notice.regions)}")
    if notice.apply_end:
        lines.append(f"· 접수 마감: {notice.apply_end.isoformat()}")
    lines.append("")
    for reason in result.reasons:
        lines.append(f"· {reason}")
    lines.append("")
    lines.append("⚠️ 최종 자격은 공고문 원문 확인 필수")

    return "\n".join(lines), notice.detail_url


def build_reminder(notice: Notice, kind: str) -> tuple[str, str | None]:
    if kind == "start":
        header = "🚀 오늘부터 접수 시작!"
    else:
        header = "⏰ 오늘 접수 마감!"
    lines = [header, "", f"[{notice.source}] {notice.title}"]
    if notice.apply_start:
        lines.append(f"· 접수 시작: {notice.apply_start.isoformat()}")
    if notice.apply_end:
        lines.append(f"· 접수 마감: {notice.apply_end.isoformat()}")
    return "\n".join(lines), notice.detail_url


def build_error_notice(source: str, detail: str) -> str:
    return f"🔴 수집 실패 알림\n{source} 수집이 실패했습니다.\n사유: {detail}"
