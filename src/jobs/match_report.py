"""DB에 쌓인 공고 전체에 매칭을 돌려 결과표를 출력한다.
python -m src.jobs.match_report
"""
import sqlite3

from src.matcher import match
from src.profile import load_profile
from src.store import Store

DB_PATH = "data/notices.db"


def main() -> None:
    profile = load_profile("profile.yaml" if _exists("profile.yaml") else "profile.example.yaml")
    store = Store(DB_PATH)
    try:
        rows = store.conn.execute("SELECT id FROM notices ORDER BY source, id").fetchall()
        counts = {"MATCH": 0, "NEEDS_REVIEW": 0, "NO_MATCH": 0}
        for row in rows:
            notice = store.get(row["id"])
            result = match(notice, profile)
            counts[result.verdict] += 1
            print(f"[{result.verdict:12}] {notice.source} | {notice.title}")
            for reason in result.reasons:
                print(f"               - {reason}")
        print()
        print(f"합계: MATCH {counts['MATCH']} / NEEDS_REVIEW {counts['NEEDS_REVIEW']} / NO_MATCH {counts['NO_MATCH']}")
    finally:
        store.close()


def _exists(path: str) -> bool:
    from pathlib import Path
    return Path(path).exists()


if __name__ == "__main__":
    main()
