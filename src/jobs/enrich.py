"""NEEDS_REVIEW 후보 중 조건 추출이 안 된 공고만 PDF/상세텍스트를 읽어
나이·자산·차량가액 조건을 채운다. NO_MATCH는 건드리지 않는다(불필요한 PDF 요청 방지).
python -m src.jobs.enrich
"""
from pathlib import Path

from src.enricher.condition_parse import parse_conditions
from src.enricher.pdf_extract import extract_lh_pdf_text
from src.matcher import match
from src.profile import load_profile
from src.store import Store

DB_PATH = "data/notices.db"


def _profile_path() -> str:
    return "profile.yaml" if Path("profile.yaml").exists() else "profile.example.yaml"


def run() -> dict:
    profile = load_profile(_profile_path())
    store = Store(DB_PATH)
    enriched = []
    try:
        for notice in store.all():
            if notice.conditions is not None:
                continue
            if match(notice, profile).verdict == "NO_MATCH":
                continue

            if notice.source == "LH":
                text = extract_lh_pdf_text((notice.raw or {}).get("file_ids"))
                source_label = "pdf"
            else:
                text = (notice.raw or {}).get("detail_text")
                source_label = "detail_html"

            if not text:
                continue

            conditions = parse_conditions(text, source_label)
            store.set_conditions(notice.id, conditions)
            enriched.append((notice, conditions))
    finally:
        store.close()
    return {"enriched": enriched}


def main() -> None:
    result = run()
    print(f"조건 추출 {len(result['enriched'])}건")
    for notice, conditions in result["enriched"]:
        print(f"  [{notice.source}] {notice.title} -> {conditions}")


if __name__ == "__main__":
    main()
