"""Phase 0: LH청약플러스 임대주택 공고 목록 크롤링 실측.

오픈API 대신 크롤링을 채택 (data.go.kr 활용신청이 API 상품마다 필요해 번거롭고,
목록 페이지가 정적 HTML이라 API보다 오히려 얻는 정보가 많음).

실행: python research/probe_lh.py
결과: research/samples/lh_list.html 저장 + 첨부 PDF 1건 다운로드/텍스트 추출 테스트.
"""
import pathlib
import httpx
import pdfplumber
from bs4 import BeautifulSoup

LIST_URL = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"
FILE_LIST_URL = "https://apply.lh.or.kr/lhapply/wt/wrtanc/wrtFileDownl.do"
FILE_DOWNLOAD_URL = "https://apply.lh.or.kr/lhapply/lhFile.do"
HEADERS = {"User-Agent": "lh-sh-alert-research/0.1 (personal notice checker)"}
SAMPLES_DIR = pathlib.Path(__file__).parent / "samples"


def fetch_list() -> str:
    resp = httpx.get(LIST_URL, headers=HEADERS, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table.bbs_ListA tbody tr, table tbody tr"):
        cells = [c.get_text(strip=True) for c in tr.select("td")]
        if len(cells) < 8:
            continue
        title_a = tr.select_one("a.wrtancInfoBtn")
        file_a = tr.select_one("a.listFileDown")
        rows.append(
            {
                "no": cells[0],
                "housing_type": cells[1],
                "title": cells[2],
                "region": cells[3],
                "has_attachment": "있음" in cells[4],
                "posted_at": cells[5],
                "deadline": cells[6],
                "status": cells[7],
                "pan_id": title_a.get("data-id1") if title_a else None,
                "file_ids": (
                    {
                        "uppAisTpCd": file_a.get("data-id1"),
                        "aisTpCd": file_a.get("data-id2"),
                        "ccrCnntSysDsCd": file_a.get("data-id3"),
                        "lsSst": file_a.get("data-id4"),
                        "panId": file_a.get("data-id5"),
                    }
                    if file_a
                    else None
                ),
            }
        )
    return rows


def fetch_file_list(file_ids: dict) -> list[dict]:
    resp = httpx.post(
        FILE_LIST_URL,
        data={
            "uppAisTpCd1": file_ids["uppAisTpCd"],
            "aisTpCd1": file_ids["aisTpCd"],
            "ccrCnntSysDsCd1": file_ids["ccrCnntSysDsCd"],
            "lsSst1": file_ids["lsSst"] or "",
            "panId1": file_ids["panId"],
        },
        headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def download_pdf(file_id: int, out_path: pathlib.Path) -> None:
    resp = httpx.get(FILE_DOWNLOAD_URL, params={"fileid": file_id}, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    out_path.write_bytes(resp.content)


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    html = fetch_list()
    (SAMPLES_DIR / "lh_list.html").write_text(html, encoding="utf-8")

    rows = parse_rows(html)
    print(f"목록에서 파싱된 공고 수: {len(rows)}")
    for row in rows[:3]:
        print(" -", row["housing_type"], "|", row["region"], "|", row["posted_at"], "~", row["deadline"], "|", row["status"], "|", row["title"])

    attachment_row = next((r for r in rows if r["has_attachment"] and r["file_ids"]), None)
    if not attachment_row:
        print("첨부파일 있는 공고를 찾지 못함.")
        return

    files = fetch_file_list(attachment_row["file_ids"])
    pdf_file = next((f for f in files if f["cmnAhflNm"].lower().endswith(".pdf")), None)
    if not pdf_file:
        print("PDF 첨부가 없어 hwp/기타 파일만 확인됨:", [f["cmnAhflNm"] for f in files])
        return

    out_pdf = SAMPLES_DIR / "lh_sample.pdf"
    download_pdf(pdf_file["cmnAhflSn"], out_pdf)
    print(f"PDF 다운로드 완료: {out_pdf} ({out_pdf.stat().st_size} bytes)")

    with pdfplumber.open(out_pdf) as pdf:
        print(f"PDF 페이지 수: {len(pdf.pages)}")
        text = pdf.pages[0].extract_text() or ""
        print("첫 페이지 텍스트 미리보기:", text[:300])


if __name__ == "__main__":
    main()
