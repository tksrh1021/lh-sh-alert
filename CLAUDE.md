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

## 현재 Phase
Phase 3 완료 (알림, pytest 35개 통과, 실제 카카오톡 발송 검증) → Phase 4(조건 자동 추출) 또는 배포(GitHub Actions/DB 영속화) 결정 대기

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
