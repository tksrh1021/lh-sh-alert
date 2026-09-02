"""카카오가 죽었을 때 쓰는 2차 채널. Discord webhook."""
import httpx

from src.env import load_env


class BackupSendError(Exception):
    pass


def send_discord(text: str) -> None:
    env = load_env()
    webhook_url = env.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise BackupSendError("DISCORD_WEBHOOK_URL이 .env에 없어 백업 채널을 쓸 수 없음")

    resp = httpx.post(webhook_url, json={"content": text}, timeout=15)
    if resp.status_code >= 300:
        raise BackupSendError(f"Discord 발송 실패: {resp.status_code} {resp.text}")
