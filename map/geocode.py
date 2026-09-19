"""map/data/*.json의 단지 주소를 카카오 로컬 API로 지오코딩해서 lat/lng을 채운다.
python -m map.geocode map/data/happy2026-2.json
"""
import json
import sys
import time

import httpx

from src.env import load_env

GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def geocode(address: str, api_key: str) -> tuple[float, float] | None:
    resp = httpx.get(
        GEOCODE_URL, params={"query": address}, headers={"Authorization": f"KakaoAK {api_key}"}, timeout=10
    )
    resp.raise_for_status()
    docs = resp.json()["documents"]
    if not docs:
        return None
    return float(docs[0]["y"]), float(docs[0]["x"])  # (lat, lng)


def main(path: str) -> None:
    api_key = load_env().get("KAKAO_REST_API_KEY")
    with open(path, encoding="utf-8") as f:
        complexes = json.load(f)

    failed = []
    for c in complexes:
        address = c["address"]
        latlng = geocode(address, api_key)
        if not latlng and ")" in address:
            # 괄호(동 이름) 뒤에 건물 애칭이 붙어 있으면 카카오가 못 찾는 경우가
            # 있어서, 그 부분을 떼고 한 번 더 시도
            time.sleep(0.3)
            latlng = geocode(address[: address.rindex(")") + 1], api_key)
        if latlng:
            c["lat"], c["lng"] = latlng
        else:
            failed.append(c.get("name") or address)
        time.sleep(0.3)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(complexes, f, ensure_ascii=False, indent=2)

    print(f"{len(complexes)}개 중 {len(failed)}개 지오코딩 실패")
    for name in failed:
        print("  -", name)


if __name__ == "__main__":
    main(sys.argv[1])
