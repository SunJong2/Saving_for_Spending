# 모아사(moasa) 프로젝트 인수인계 문서

새 대화에서 이 문서를 첨부하고 "이 문서 읽고 이어서 진행하자"라고 하면 됨.
그 세션에서 작업할 코드 파일도 함께 첨부할 것.

---

## 1. 학습자 & 멘토링 방식 (중요 — 반드시 유지)

- 홍익대 컴퓨터공학과 3학년(군 복학). C/파이썬 기초만 있던 상태에서 첫 프로젝트로 시작
- 목표: 삼성전자 DS·SK하이닉스·금융권 IT·네이버·카카오·토스, SSAFY 입과
- **멘토링 규칙:**
  - "한 번에 하나씩" — 정보 과부하 금지, 단계별 진행
  - 코드를 통째로 주지 않기 — 학습자가 직접 짜보고 리뷰받는 방식 우선. 새 개념만 예시 코드 제공
  - 모든 코드에 "왜 이렇게 하는지" 설명 필수
  - 학습자를 "님"이라고 지칭하지 말 것 (호칭 없이 대화)
  - 존댓말 사용 (학습자는 반말)
  - 버그는 답을 바로 주지 말고 단서를 주며 스스로 찾게 유도 (단, 막히면 풀어줌)
  - 설계 판단은 선택지 A/B/C로 제시하고 트레이드오프 설명 후 학습자가 결정
  - 배운 개념이 재등장하면 "그때 그거"로 연결해주기

## 2. 프로젝트 개요

- **이름: 모아사 (moasa)** — "모아서 사는 재미" 슬로건
- 컨셉: 소비를 위한 저축 앱. 단기 구매 목표(예: 자켓 30만원)를 세우고, 참은 소비(치킨 안 시킴 +2만원)를 가상 적립해 목표 달성
- 톤: "혼내지 않는" 긍정적 절약. 문구는 질문형("얼마를 아꼈나요?")
- 디자인: 흰 배경 + 토스풍 미니멀 + 보라→파랑 그라데이션(#7C4DFF→#448AFF), max-width 480px 모바일 우선

## 3. 기술 스택 & 배포

- Backend: Python + FastAPI + PostgreSQL(Supabase) + JWT(python-jose) + bcrypt(passlib) + python-dotenv
- Frontend: vanilla HTML/CSS/JS (프레임워크 없음)
- 배포: **Render(무료, moasa.onrender.com)** + **Supabase PostgreSQL(무료, 영구)**
- DB 연결: psycopg + `with get_db() as conn:` 컨텍스트 매니저 (database.py의 @contextmanager)
- 환경변수: SECRET_KEY, DATABASE_URL (.env는 gitignore, Render 대시보드에 등록됨)
- 개발 흐름: 로컬 수정 → localhost 테스트 → 커밋/push → Render 자동 재배포
- SQLite → PostgreSQL 전환 완료 (배포 후 "database is locked" 문제 겪고 전환. README 스토리 재료)

## 4. 파일 구조

```
SavingApp/
├── main.py          # 라우터 등록, StaticFiles, init_db(), 루트→login 리다이렉트
├── database.py      # get_db() 컨텍스트 매니저, init_db()
├── auth.py          # /signup, /login, get_current_user, /me
├── goals.py         # /goals CRUD + history + {goal_id}/savings
├── savings.py       # /savings CRUD
├── static/
│   ├── style.css    # 디자인 시스템 (CSS 변수, 버튼/모달/탭바/진행률바)
│   ├── login.html, signup.html
│   ├── index.html   # 홈 (저금통, 기록 목록, 각종 모달)
│   ├── add-goal.html, add-saving.html, edit-goal.html
│   └── history.html
├── .env, requirements.txt, runtime.txt (python-3.12.7)
```

## 5. DB 스키마 (PostgreSQL)

- users: id SERIAL PK, email UNIQUE, password_hash, nickname, created_at
- goals: id, user_id FK, name, target_amount, current_amount(DEFAULT 0), deadline, is_completed BOOLEAN(DEFAULT FALSE), image_url, created_at, completed_at
- savings: id, user_id FK, goal_id FK, category, amount, memo, image_url, created_at
- 플레이스홀더 %s, 불리언 TRUE/FALSE 사용

## 6. 확립된 설계 원칙 (면접/README 재료)

- 목표는 한 번에 하나 (is_completed로 구분, 히스토리 겸용)
- 초과 달성 이월 안 함 (가상 적립이라 금액=노력의 기록. progress는 안 자르고 바 그래픽만 100 제한)
- target_amount 수정 시 current 이하 금지 (C안: 재판정 복잡성 제거)
- 기록은 삭제만, 수정 없음 / 완료 목표 기록은 동결
- id 지목 API는 소유권 검사 실패 시 404 (IDOR 방어, 존재 은닉)
- 400=형식 오류, 409=상태 충돌(중복), 401=인증
- 마감 연장 = deadline PATCH (스케줄러 없이 d_day<0 게으른 판정)
- 파생값(progress, d_day)은 저장 안 하고 계산
- 날짜 차이는 .date() 정규화 후 계산
- "문지기는 문 앞에"(검증 먼저), "클라이언트를 믿지 않는다"(백엔드 검증 필수)
- 이미지 기능 보류 (image_url 컬럼은 유지, 향후 퀵버튼용)
- 문구는 프론트, 데이터는 백엔드

## 7. 완성된 것

- 백엔드 전체 (인증, goals/savings CRUD, 히스토리, 검증, IDOR 방어)
- 프론트 전체 화면 + 진입가드(토큰 1차/401 2차) + 모달들(축하/삭제확인/기록상세/히스토리상세)
- 네비게이션 (헤더, 하단 탭바, 로그아웃, 뒤로가기)
- 마감 초과 배너 + 연장 유도
- 배포 (Render + Supabase) 정상 동작

## 8. 현재 진행 중: 폰 UI 문제 수정

발견된 문제 목록과 상태:

| # | 문제 | 상태 |
|---|------|------|
| 1,5 | 홈/히스토리 스크롤 불가·잘림 | ✅ 해결 (container의 flex 제거 + "has tabbar" 오타를 "has-tabbar"로) |
| 2 | 날짜 입력칸 iOS에서 삐져나옴 | CSS 수정 적용했으나 **폰에서 최종 확인 필요** (input[type="date"]에 -webkit-appearance:none 등) |
| 7,8,9 | **버튼 연타 시 중복 제출** (기록 3~5개 중복) | ⬜ 미해결. 프론트에 isSubmitting 깃발+try/finally+버튼 disabled 적용 예정 (add-saving, add-goal, edit-goal, 삭제 함수들 전부) |
| 6 | created_at이 UTC로 저장됨 (9시간 차이) | ⬜ 미해결. KST = timezone(timedelta(hours=9)) 정의하고 datetime.now(KST)로 교체 예정 |
| 3 | 기록 상세 모달 금액 32px가 폰에서 큼 | ⬜ 나중 (26px 정도로) |
| 4 | edit-goal 로딩 중 빈 칸 노출 | ⬜ 나중 (스피너나 폼 숨김) |

- 폰 테스트: 카페 와이파이(client isolation)와 핫스팟(IP 미할당) 문제로 로컬 폰 테스트 실패 → 맥 사파리 반응형 디자인 모드로 대체 중. 최종 확인만 배포로

## 9. 남은 로드맵

1. 위 UI 문제 마무리 (중복 제출이 최우선)
2. 홈 레이아웃 다듬기: 이모지→아이콘(Lucide 등), 저금통 개선, CSS 리팩토링(반복 인라인→클래스), favicon/apple-touch-icon
3. 부가 기능 택1~2: 퀵 버튼, streak, 통계(GROUP BY), 환산 표시
4. PWA (manifest.json)
5. 데모 계정 정성껏 만들기 + README 작성 (설계 판단 중심, 주차별 정리 문서가 재료)

## 10. 새 대화 시작할 때

- 이 문서 첨부 + "이어서 진행하자"
- **그 세션에서 작업할 코드 파일 첨부** (예: 중복 제출 작업이면 add-saving.html, add-goal.html, edit-goal.html / 백엔드 작업이면 해당 .py)
- 진행하다 과거 결정의 이유가 궁금하면 과거 대화 검색 요청 가능
