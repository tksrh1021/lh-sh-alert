"""카카오 우선, 실패하면 백업 채널. 둘 다 실패하면 조용히 넘기지 않고 예외를 던진다."""
from src.notifier.backup import BackupSendError, send_discord
from src.notifier.kakao import KakaoSendError, send_kakao


class NotifyError(Exception):
    pass


def notify(text: str, link_url: str | None = None) -> str:
    try:
        send_kakao(text, link_url)
        return "kakao"
    except KakaoSendError as kakao_error:
        try:
            send_discord(f"[카카오 발송 실패로 백업 채널 사용]\n{text}")
            return "discord"
        except BackupSendError as backup_error:
            raise NotifyError(
                f"카카오 실패({kakao_error}), 백업 채널도 실패({backup_error})"
            ) from backup_error
