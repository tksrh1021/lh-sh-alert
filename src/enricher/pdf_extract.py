"""LH 공고 첨부 PDF를 받아 텍스트로 바꾼다. research/probe_lh.py에서 검증한 흐름 그대로.
매칭 후보로 좁혀진 공고에만 쓴다 — 모든 공고마다 PDF를 받으면 LH 서버에 부담."""
import httpx
import pdfplumber
import io

from src.config import LH_FILE_DOWNLOAD_URL, LH_FILE_LIST_URL, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}


def extract_lh_pdf_text(file_ids: dict | None) -> str | None:
    if not file_ids or not file_ids.get("panId"):
        return None

    files = _fetch_file_list(file_ids)
    pdf_file = next((f for f in files if f["cmnAhflNm"].lower().endswith(".pdf")), None)
    if not pdf_file:
        return None

    pdf_bytes = _download(pdf_file["cmnAhflSn"])
    if not pdf_bytes:
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return None


def _fetch_file_list(file_ids: dict) -> list[dict]:
    try:
        resp = httpx.post(
            LH_FILE_LIST_URL,
            data={
                "uppAisTpCd1": file_ids.get("uppAisTpCd"),
                "aisTpCd1": file_ids.get("aisTpCd"),
                "ccrCnntSysDsCd1": file_ids.get("ccrCnntSysDsCd"),
                "lsSst1": file_ids.get("lsSst") or "",
                "panId1": file_ids.get("panId"),
            },
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError):
        return []


def _download(file_id: int) -> bytes | None:
    try:
        resp = httpx.get(LH_FILE_DOWNLOAD_URL, params={"fileid": file_id}, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError:
        return None
