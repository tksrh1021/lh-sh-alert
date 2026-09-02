"""환경변수 읽기/쓰기. 로컬은 `.env` 파일, GitHub Actions는 Secrets가 OS 환경변수로
주입되므로 os.environ을 기본값으로 깔고 `.env`가 있으면 그 값으로 덮어쓴다."""
import os
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(updates: dict) -> None:
    env = load_env()
    env.update(updates)
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8")
