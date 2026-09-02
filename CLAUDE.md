# 프로젝트: LH/SH 공공임대 공고 알림 봇

## 목적
LH·SH 임대주택 모집공고를 수집해, 내 조건에 맞는 공고를 카카오톡으로 알린다.
접수 마감 전 리마인드도 보낸다. 개인용 단일 사용자 도구.

## 설계서
전체 설계는 `docs/설계서.md` 참조. 구조를 바꾸려면 먼저 설계서를 갱신할 것.

## 기술 스택
Python 3.11+ / httpx / BeautifulSoup4 / pdfplumber / pydantic / SQLite / pytest
스케줄: GitHub Actions

## 절대 규칙
1. 네트워크 호출은 `tests/fixtures/`에 저장된 응답으로 테스트한다. 테스트가 실제 사이트를 때리면 안 된다.
2. 파싱 실패와 "결과 없음"을 구분한다. 셀렉터가 안 맞으면 예외를 던지고, 빈 리스트를 반환하지 않는다.
3. 자격 판단 애매하면 NO_MATCH가 아니라 NEEDS_REVIEW다. 오탈락 > 오알림이라는 판단을 항상 지킨다.
4. `profile.yaml`, `.env`는 절대 커밋하지 않는다. 소득·자산 정보가 들어 있다.
5. 로그에 소득·자산 금액을 출력하지 않는다.
6. 소득 기준 금액을 코드에 하드코딩하지 않고 `data/income_standards.yaml`에서 읽는다.
7. 자동 청약 신청 기능을 구현하지 않는다.
8. 크롤링 시 요청 간격 최소 1초, User-Agent 명시.

## 작업 방식
- 새 기능은 먼저 실패하는 테스트를 만들고 구현한다.
- 커밋은 논리 단위로 쪼갠다. Phase 하나를 한 커밋으로 만들지 않는다.
- 외부 사이트 구조에 의존하는 셀렉터/필드명은 `src/config.py`에 모은다.
- 작업 후 반드시 `pytest`를 실행하고 결과를 보고한다.

## 향후 방향 (지금 만들지 말 것)
사용자가 나중에(개인용으로 충분히 다듬어져서 상용화할 만해지면) 다중 사용자 지원을
원한다고 확인함. 지금은 절대 미리 만들지 말 것 — 본인 계정으로 검증 먼저 끝내고
나중에 요청 오면 그때 시작. 다중 사용자로 가려면 최소: (1) 사용자별 profile.yaml 저장
방식, (2) 사용자별 카카오 로그인/토큰(각자 "나에게 보내기" 인증 필요 — 번호만으론
카톡 발송 불가, 알림톡은 사업자등록+과금 필요), (3) 웹 배포(지금의 로컬 UI로는 부족).

## 현재 Phase
배포 완료 + Phase 4(나이·자산 조건 자동 추출) + 설정 UI 완료. pytest 65개 통과.

## 설정 UI + 프로필 배포 구조 (중요)
- **버그였던 것**: `profile.yaml`은 민감정보라 `.gitignore`에 있었는데, 그러면 GitHub Actions가 이 파일을 절대 못 본다. 그래서 배포 이후 지금까지 실제로는 `profile.example.yaml`(예시값)로만 판정이 돌아갔었다 — 실제 프로필은 만들어진 적도 없었음.
- **해결**: `python -m src.jobs.settings_ui` — 로컬 웹폼(stdlib http.server, Flask 없음)에서 나이/자산/관심유형/관심지역/조용한시간을 입력하면 (1) 로컬 `profile.yaml` 저장 (2) GitHub Actions Secret `PROFILE_YAML`에 통째로 암호화해서(`src/github_secrets.py`, PyNaCl sealed box) 업로드까지 자동으로 한다.
- Actions 쪽은 `collect.yml`/`remind.yml` 맨 앞에 "프로필 복원" 스텝을 추가해 `echo "$PROFILE_YAML" > profile.yaml`로 시크릿을 파일로 복원한 뒤 기존 로직 그대로 실행. 시크릿이 아직 없으면 빈 파일을 만들지 않고 `profile.example.yaml`로 자연스럽게 폴백.
- 이 UI를 쓰려면 `.env`에 `GITHUB_PAT`(리포의 Secrets 쓰기 권한 필요)와 `GITHUB_REPO`("계정명/저장소명")가 있어야 함.
- **프로필 스키마도 같이 정리함**: 소득/세대/청약통장/거주지 등 매처가 실제로 안 쓰는 필드를 전부 뺐다. 지금 Profile은 `personal.birth_date`, `assets.total_asset_krw/car_value_krw`, `interests.housing_types/target_groups/regions`, `notify.quiet_hours`뿐 — UI 폼도 이 6개만 물어본다.

## Phase 4 확정 사항 (사용자 결정)
- **소득은 자동판단 대상에서 제외**: 공고마다 표(가구원수x대상계층x순위) 표현이 제각각이고 숫자 밀집도가 높아 규칙 기반으로 안전하게 못 뽑는다고 판단. `data/income_standards.yaml`도 더 이상 채울 계획 없음(비워둔 채 유지).
- 나이(`만 OO세 이상 OO세 이하`)와 자산/차량가액(`총자산가액 합산기준 OOO만원`, `자동차가액이 OOO만원`) 두 가지만 규칙 기반(`src/enricher/condition_parse.py`)으로 추출. 실제 LH PDF로 검증 완료(만19~39세, 3억4500만원, 4542만원 — 전부 정확히 일치).
- 순위별로 기준액이 다르면(완화조건 등) **가장 관대한(높은) 값**을 채택 — 오탈락 방지가 우선이라는 기존 원칙 유지.
- `notice.conditions`가 채워지고 `extraction_confidence > 0`이면 나이/자산 기준으로 실제 MATCH/NO_MATCH 판정. 못 뽑으면(confidence 0) 여전히 NEEDS_REVIEW.
- `src/jobs/enrich.py`: NO_MATCH가 이미 확실한 공고는 PDF/상세텍스트를 아예 안 읽음(불필요한 요청 방지). SH는 collect() 때 이미 받아둔 상세 텍스트를 재사용, LH만 이 시점에 PDF를 새로 받음.
- **지역 필터 변경**: 거주지/근무지에서 유추하던 방식 폐기, `profile.yaml`에 `interests.regions`(관심 시/도 목록)를 명시 설정하는 방식으로 변경 — 사용자가 원하는 지역만 명확히 지정.
- **알려진 한계**: Phase 4 이전에 수집된 SH 공고 일부는 `raw.detail_text`가 없는 옛날 스키마로 저장돼 있어 조건 추출이 안 됨(자연 소멸 — 내용이 안 바뀌면 재수집해도 안 갱신됨). 새로 들어오는 공고는 문제없음.
- 그 다음은 Phase 5(P2, 선택) — 대시보드/발표일 리마인드/타 지방공사 확장.

## 리마인드 정책 변경 (사용자 요청)
D-3/D-1/D-0 다단계 리마인드 대신 **접수 시작일 1번 + 접수 마감일 1번, 총 두 번만** 보내도록 단순화함.
- SH: 상세 페이지에서 '청약신청 일정' 구간을 찾아 접수 시작/마감을 둘 다 추출 (`normalizer.parse_schedule_dates`). 공고마다 헤딩 표현이 달라서("청약신청 일정" vs "청약신청 :") 정규식 하나로 못 잡고, "청약신청" 뒤에 날짜가 바로 오는 진짜 위치만 찾도록 처리. "청약신청서.pdf" 같은 첨부파일명 오탐도 실측 중 발견해서 제외 처리함.
- LH: 목록에 접수 시작일 자체가 없어서 마감일 리마인드만 가능 (시작일 리마인드는 Phase 4에서 PDF까지 읽어야 지원 가능).
- `profile.yaml`의 `notify.reminder_days_before`는 더 이상 안 씀 — 스키마에서 제거.

## 배포 확정 사항
- DB 영속화 방식: **git commit-back** 채택 (원격 DB/캐시 대신). Actions가 매 실행 후 `data/notices.db`를 커밋+푸시. 이유: 새 계정/서비스 없이 무료로 되는 가장 단순한 방법 (설계서 4.3 우려사항 중 (a)안).
- 스케줄: `collect.yml`은 30분 간격 상시 실행(설계서의 주/야간 빈도 분리는 Actions 무료 한도 안에서 불필요해 단순화함, ponytail 주석 남김). `remind.yml`은 매일 00:00 UTC(=09:00 KST).
- `src/env.py`가 os.environ을 우선 깔고 `.env`로 덮어쓰는 구조로 바뀜 — 로컬은 `.env`, GitHub Actions는 Secrets가 그대로 동작.
- `src/jobs/collect.py`: LH/SH 중 하나가 깨져도 나머지는 계속 수집하고, 깨진 쪽은 에러 알림을 보냄(카카오→실패시 Discord).
- **알려진 한계**: 카카오 refresh_token이 회전(rotate)되면 로컬 `.env`엔 반영되지만 GitHub Secrets엔 자동 반영 안 됨 — Actions 환경에선 새 토큰이 유실된다. 이 경우 다음 실행에서 카카오 발송이 실패 → Discord 백업 채널로 "재인증 필요" 알림이 감(백업 채널을 설정해뒀다면). 발생하면 `research/kakao_oauth.py`를 로컬에서 다시 돌려 새 refresh_token을 받아 GitHub Secret을 수동 갱신해야 함.
- `data/notices.db`는 공개 공고 정보만 담고 있어 (개인 소득/자산 없음) 리포에 커밋해도 안전. `profile.yaml`/`.env`는 여전히 `.gitignore`.

## Phase 2 확정 사항
- notice.conditions(나이/소득/자산)는 Phase 4 전까지 항상 비어 있음 → 지금은 유형/지역/마감일만으로 NO_MATCH를 걸러내고, 나머지는 전부 NEEDS_REVIEW. MATCH는 Phase 4에서 조건 데이터가 채워져야 나온다.
- SH 게시판에는 입주자 모집과 무관한 글(용역평가, 위원회 발표 등)이 섞여 있어 유형 키워드가 안 걸리면 NEEDS_REVIEW로 새는 노이즈가 있음 — 알림 발송 전 한 번 더 걸러낼지 결정할 것.
- data/income_standards.yaml은 여전히 비어 있음 — 실제 공고문 확인 후 채워야 함 (추정 금지).

## Phase 3 확정 사항
- 카카오 우선, 실패 시 Discord webhook으로 자동 전환(`src/notifier/dispatch.py`). DISCORD_WEBHOOK_URL은 아직 미설정 — 실제 백업 채널 검증은 안 됨(유닛테스트로만 확인).
- 발송 이력은 `notifications` 테이블(notice_id+kind)로 중복 방지. 리마인드는 D-3/D-1/D-0마다 별도 kind라 각각 한 번씩만 감.
- quiet_hours(23:00-08:00) 실제로 걸리는 것까지 실측 확인함 — 정상 동작.
- **버그 수정 이력**: remind.py가 처음엔 매칭 여부(NO_MATCH) 상관없이 마감 임박한 공고를 전부 리마인드하던 버그가 있었음. 실제 DB로 돌려보다 발견, matcher 필터 추가로 수정.
- LH만 apply_end(마감일)가 있어서 리마인드가 지금은 LH에만 작동함. SH는 상세 페이지 파싱(Phase 4 근처)이 있어야 리마인드 가능.
- **아직 안 정함**: GitHub Actions 스케줄링, SQLite 영속화 방식(커밋 vs 원격 DB vs 자체 서버) — 설계서가 "장단점 제시 후 사용자가 고르라"고 명시한 부분, 아직 미결정.

## Phase 0 확정 사항 (중요)
- LH·SH 모두 오픈API 없이 크롤링만으로 진행한다. `DATA_GO_KR_KEY` 불필요.
- LH: 목록 페이지(GET, 정적 HTML)에 유형/지역/공고일/마감일/상태가 이미 있음. "상세보기"는 NetFunnel 게이트가 있어 사용하지 않는다.
- SH: 상세 페이지(POST) 인라인 HTML 텍스트가 1차 정보원. PDF(Innorix/Synap)는 최후 수단으로만 고려한다.
- 카카오 "나에게 보내기"는 OAuth 인증 완료, `KAKAO_REFRESH_TOKEN` 확보됨.
