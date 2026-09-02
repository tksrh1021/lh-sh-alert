"""외부 사이트에 의존하는 URL/셀렉터를 모아두는 곳.
사이트 구조가 바뀌면 여기만 고치면 된다 (CLAUDE.md 규칙)."""

USER_AGENT = "lh-sh-alert/0.1 (personal notice checker; contact: local use only)"
REQUEST_DELAY_SECONDS = 1.0

LH_LIST_URL = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"
LH_FILE_LIST_URL = "https://apply.lh.or.kr/lhapply/wt/wrtanc/wrtFileDownl.do"
LH_FILE_DOWNLOAD_URL = "https://apply.lh.or.kr/lhapply/lhFile.do"

SH_LIST_URL = "https://www.i-sh.co.kr/app/lay2/program/S48T1581C563/www/brd/m_247/list.do?multi_itm_seq=2"
SH_DETAIL_URL = "https://www.i-sh.co.kr/app/lay2/program/S48T1581C563/www/brd/m_247/view.do"

# 제목에서 주택 유형을 유추할 때 쓰는 키워드. LH 검색페이지(apply.lh.or.kr/lhapply/apply/sc/list.do)
# 실측으로 확인한 공식 임대주택 세부유형 13종 + SH 자체 유형(청년안심주택 등) 추가.
HOUSING_TYPE_KEYWORDS = [
    "통합공공임대", "국민임대", "공공임대", "영구임대", "행복주택(신혼희망)", "행복주택",
    "장기전세", "신축다세대매입임대", "가정어린이집", "매입임대", "전세임대",
    "집주인임대", "6년 공공임대주택", "청년안심주택", "청년매입임대", "청년전세임대",
    "도시형생활주택",
]

# 제목에서 대상 계층을 유추할 때 쓰는 키워드. LH/SH 목록 어디에도 컬럼으로
# 안 주기 때문에 제목 텍스트에서 추측하는 수밖에 없다 (Phase 4 조건 추출 전 임시).
TARGET_GROUP_KEYWORDS = [
    "청년", "신혼부부", "신생아", "한부모가족", "고령자", "대학생", "다자녀",
]

# LH 목록의 실제 지역 표기 기준 17개 시/도. 설정 UI 체크박스에 씀.
REGIONS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]
